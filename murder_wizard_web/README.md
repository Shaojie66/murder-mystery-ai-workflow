# Murder Wizard Web - 剧本杀创作工作流 Web 版

基于 FastAPI + React 的剧本杀创作工作流管理平台。

## 快速开始

### 本地开发

```bash
# 方式1: 使用启动脚本（一键启动）
./start.sh

# 方式2: 手动启动
# Terminal 1: 启动后端
cd murder_wizard_web/backend
PYTHONPATH=. python main.py

# Terminal 2: 启动前端
cd murder_wizard_web/frontend
npm run dev
```

访问 http://localhost:5173

### Docker 部署

```bash
cd murder_wizard_web

# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

访问 http://localhost:3000

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_PROVIDER` | `claude` | LLM 提供商: `claude`, `openai`, `ollama` |
| `ANTHROPIC_API_KEY` | - | Claude API 密钥 |
| `OPENAI_API_KEY` | - | OpenAI API 密钥 |

## 功能模块

- **项目管理**: 创建、查看、删除剧本杀项目
- **阶段执行**: 8阶段完整工作流，支持 SSE 实时输出
- **产物编辑**: Monaco 编辑器，支持 Markdown 预览
- **信息矩阵**: 角色-事件认知状态管理
- **穿帮审计**: 自动检测剧本一致性问题
- **消耗统计**: API 调用成本可视化

## 技术栈

- **后端**: FastAPI, SSE, Python 3.11+
- **前端**: React 18, TypeScript, Tailwind CSS, Vite
- **数据**: 存储在 `~/.murder-wizard/projects/`

## 项目结构

```
murder_wizard_web/
├── backend/                 # FastAPI 后端
│   ├── main.py             # 应用入口
│   ├── murder_wizard/       # murder_wizard 包（含 api/ 和 core/ 子包）
│   │   ├── api/            # REST API 路由
│   │   │   ├── projects.py
│   │   │   ├── phases.py
│   │   │   ├── files.py
│   │   │   ├── matrix.py
│   │   │   ├── costs.py
│   │   │   ├── audit.py
│   │   │   └── pdf.py
│   │   └── core/           # 核心模块
│   │       ├── phase_runner_web.py  # Web 版阶段执行器
│   │       └── sse_manager.py       # SSE 连接管理
│   └── requirements.txt
├── frontend/                # React 前端
│   ├── src/
│   │   ├── pages/          # 页面组件
│   │   ├── api/            # API 客户端
│   │   ├── stores/         # Zustand 状态管理
│   │   └── types/          # TypeScript 类型
│   ├── Dockerfile
│   └── nginx.conf          # 生产 nginx 配置
├── docker-compose.yml
└── start.sh               # 本地开发启动脚本
```

## API 端点

基础路径: `/api`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/projects` | 列出所有项目 |
| POST | `/projects` | 创建项目 |
| GET | `/projects/{name}` | 获取项目详情 |
| DELETE | `/projects/{name}` | 删除项目 |
| POST | `/projects/{name}/phases/{stage}/run` | 运行指定阶段 (SSE) |
| POST | `/projects/{name}/expand` | 原型扩写 (SSE) |
| POST | `/projects/{name}/audit` | 穿帮审计 (SSE) |
| GET | `/projects/{name}/files` | 列出文件 |
| GET | `/projects/{name}/files/{filename}` | 读取文件 |
| PUT | `/projects/{name}/files/{filename}` | 保存文件 |
| GET | `/projects/{name}/matrix` | 获取信息矩阵 |
| PUT | `/projects/{name}/matrix/cells/{char}/{event}` | 更新认知状态 |
| GET | `/projects/{name}/costs` | 获取消耗统计 |
| GET | `/projects/{name}/audit/report` | 获取审计报告 |

详细 API 文档: http://localhost:8000/docs
