"""多文件提交：先逐字节备份，再逐文件「临时文件 + os.replace」写入，失败自动从备份恢复。

只承诺模型失败与普通写入异常（含 KeyboardInterrupt）的恢复；不承诺 kill -9 / 断电时的
多文件原子性（那需要版本目录或 journal，属另行批准的设计）。工具永不删除用户文件。
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

_replace = os.replace      # 模块级接缝，测试注入失败
_copy = shutil.copy2


@dataclass
class CommitReport:
    tag: str = ""
    backups: dict = field(default_factory=dict)      # relpath -> 备份文件名（相对 project）
    written: list = field(default_factory=list)
    restored: list = field(default_factory=list)
    restore_failed: list = field(default_factory=list)


class CommitFailed(Exception):
    def __init__(self, stage: str, problems: Sequence[str], report: CommitReport):
        super().__init__(f"{stage}: " + "；".join(problems))
        self.stage = stage            # precheck | backup | write | after_write | verify
        self.problems = list(problems)
        self.report = report


def _safe_rel(rel: str) -> bool:
    p = Path(rel)
    return not p.is_absolute() and ".." not in p.parts


def _restore(project: Path, report: CommitReport) -> None:
    """对每个备份：当前字节与备份不同则恢复并核对。绝不抛出，只清理本工具自己的临时文件。"""
    for rel, bname in report.backups.items():
        target, backup = project / rel, project / bname
        try:
            if target.read_bytes() == backup.read_bytes():
                continue
            tmp = target.with_name(target.name + ".restore_tmp")
            _copy(backup, tmp)
            _replace(tmp, target)
            if target.read_bytes() != backup.read_bytes():
                raise OSError("恢复后字节不一致")
            report.restored.append(rel)
        except BaseException:  # noqa: BLE001 - 回滚本身不得抛出
            report.restore_failed.append(rel)
    for rel in list(report.backups):
        for suffix in (".expand_tmp", ".restore_tmp"):
            tmp = (project / rel).with_name(Path(rel).name + suffix)
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass


def commit_files(
    project: Path,
    writes: Mapping[str, str],
    *,
    backup_tag: str,
    also_backup: Sequence[str] = (),
    after_write: Optional[Callable[[], None]] = None,
    verify: Optional[Callable[[], list]] = None,
    stamp: Optional[str] = None,
) -> CommitReport:
    project = Path(project)
    report = CommitReport()
    targets = list(writes) + [r for r in also_backup if r not in writes]
    bad = [r for r in targets if not _safe_rel(r)]
    missing = [r for r in targets if _safe_rel(r) and not (project / r).is_file()]
    if bad or missing:
        raise CommitFailed("precheck", [f"路径不安全：{r}" for r in bad] + [f"目标文件不存在：{r}" for r in missing], report)

    base = stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    tag, n = base, 1
    while any((project / f"{r}.{backup_tag}.{tag}").exists() for r in targets):
        n += 1
        tag = f"{base}_{n}"
    report.tag = tag
    try:
        for rel in targets:
            dest = project / f"{rel}.{backup_tag}.{tag}"
            _copy(project / rel, dest)
            report.backups[rel] = dest.name if "/" not in rel else str(Path(rel).parent / dest.name)
            if dest.read_bytes() != (project / rel).read_bytes():
                raise OSError(f"备份 {rel} 后字节不一致")
    except Exception as e:  # 一个目标都还没碰
        raise CommitFailed("backup", [f"备份失败：{e}"], report) from e

    stage = "write"
    try:
        for rel, text in writes.items():
            tmp = (project / rel).with_name(Path(rel).name + ".expand_tmp")
            with open(tmp, "wb") as fh:
                fh.write(text.encode("utf-8"))
                fh.flush()
                os.fsync(fh.fileno())
            _replace(tmp, project / rel)
            report.written.append(rel)
        if after_write is not None:
            stage = "after_write"
            after_write()
        if verify is not None:
            stage = "verify"
            problems = verify()
            if problems:
                raise CommitFailed("verify", problems, report)
    except CommitFailed:
        _restore(project, report)
        raise
    except Exception as e:
        _restore(project, report)
        raise CommitFailed(stage, [str(e)], report) from e
    except BaseException:  # KeyboardInterrupt / SystemExit：回滚后原样重抛
        _restore(project, report)
        raise
    return report
