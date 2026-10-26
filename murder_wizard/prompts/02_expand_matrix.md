# expand 第 1 步：在原型矩阵上增量扩写（2 人 3 事件 → 6 人 7 事件）

## 创意简报
{{brief_content}}

## 机制设计
{{mechanism_content}}

## 原型 a 本（原文，不得改动）
{{proto_characters_content}}

## 原型信息矩阵（JSON，E1-E3 与 R1/R2 的原认知不得改动）
{{proto_matrix_json}}

## 任务
只输出“增量”，由程序并入原型矩阵：
- 新增 4 个事件 E4、E5、E6、E7：只续写，全部晚于 E3，不得插入或改动 E1-E3；每个事件至少有一位角色“知”。
- 新增 4 位角色 R3、R4、R5、R6：每人给出 name、role、public_relationship，以及 E1-E7 全部 7 个事件的认知；每人在 E4-E7 中至少有一个非“否”。姓名六人互不相同，不含【】。
- 原有角色 R1、R2：只补 E4-E7 的认知（added_cognitions），每人 E4-E7 至少一个非“否”；绝不出现 E1-E3。
- 新增 1-6 条证据，证据 id 不得与原型冲突；认知里引用的证据必须存在。
- 认知状态只能是：知、疑、昧、否、误信、隐瞒。缺失的单元格不等于“否”，必须逐格填写。
- 凶手必须拥有核心事件的关键碎片；没有任何角色拥有全部真相。

## 输出格式
只输出一个 json 代码块，顶层键恰为 new_events、new_characters、added_cognitions、new_evidence。
下面是格式示例，只说明结构；内容必须依据简报与机制重新设计，不得照抄：

```json
{{delta_json_example}}
```
