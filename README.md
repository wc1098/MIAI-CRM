# 觅AI婚恋数字门店

本仓库是在 FastApiAdmin 基础上二次开发的全栈后台管理平台，当前面向「单品牌多门店」婚恋业务，覆盖 CRM、门店经营、活动互动、小程序对接、智慧门店大屏、云支付与后续服务工作台能力。

项目采用前后端分离架构：

- 后端：`backend/`，FastAPI、SQLAlchemy 2.x、Pydantic 2.x、Alembic、Redis、APScheduler、Uvicorn。
- 管理后台：`frontend/`，Vue 3、Vite、TypeScript、Element Plus、Pinia、Vue Router、Axios。
- 小程序/移动端：当前仓库包含 `FastApp/`、`MiniApp/`，后续业务口径以婚恋小程序为准。
- 数据库：PostgreSQL 为当前主库，Redis 用于缓存、会话与调度相关能力。
- 部署与运维：`database/`、`deploy.sh`。后端 Dockerfile 已放在 `backend/`，完整生产编排待重新设计。

## 当前业务口径

- 系统按「单品牌多门店」设计，门店是经营、权限和数据隔离的核心组织单元。
- 底层组织表仍沿用 FastApiAdmin 的 `sys_dept`，产品展示统一叫「门店」。
- 后台中「部门管理」已改为「门店管理」，`部门名称/部门编码` 对应展示为 `门店名称/门店编码`。
- `sys_user.username` 是登录账号，页面展示为「账号」。
- `sys_user.name` 是人员展示姓名，页面展示为「姓名」。
- 门店编码允许纯数字，长度 1-32 位，支付场景会使用纯数字门店编码。
- 云支付商户 ID `cp_mid` 使用启用的最顶级门店编码；云支付门店 ID `cp_store_id` 使用本系统门店 `sys_dept.id`。

## 默认本地地址

| 服务 | 默认地址 |
| --- | --- |
| 管理后台 | `http://127.0.0.1:5180` |
| 后端 API | `http://127.0.0.1:8000` |
| Swagger | `http://127.0.0.1:8000/docs` |
| API 前缀 | `/api/v1` |
| PostgreSQL | `127.0.0.1:5432` |
| Redis | `127.0.0.1:6379` |

以上端口以实际环境文件为准：`backend/env/.env.dev`、`frontend/.env.development`。

## 工程结构

```txt
miailove/
├── backend/              # 后端 FastAPI 工程
├── frontend/             # 管理后台 Vue 工程
├── FastApp/              # uni-app 移动端工程
├── MiniApp/              # 小程序相关工程
├── android_tv/           # 智慧门店大屏/电视端相关工程
├── database/             # 本地数据库 Docker Compose
├── docs/                 # 业务文档、集成说明、PRD
├── deploy.sh             # 原框架部署脚本，当前需按本项目部署形态继续改造
└── README.md
```

## 核心模块

| 模块 | 说明 |
| --- | --- |
| 系统管理 | 用户、角色、菜单、门店、岗位、字典、参数、公告、日志等基础后台能力 |
| CRM 渠道管理 | 获客入口与数据来源维护，接口前缀 `/api/v1/crm/channel` |
| CRM 线索管理 | 规划包含全量线索、门店公海、销售私海、生命周期过程记录 |
| 云支付 | 支付、预创建、小程序创建、交易查询、退款与异步通知 |
| 智慧门店大屏 | 门店大屏设备、展示与互动能力 |
| 服务工作台 | VIP 服务、合同生效后的服务工单与权益账本补齐 |
| 代码生成与监控 | 延续 FastApiAdmin 的代码生成、缓存、资源、服务监控等能力 |

当前部分 `module_miailove` 前端业务页面尚未实现，`/miailove/...` 菜单节点可先作为隐藏权限占位；实现真实 Vue 页面后再开放显示。

## 快速启动

### 1. 启动 PostgreSQL 和 Redis

本地可直接使用仓库内数据库编排：

```bash
cd database
docker compose up -d
```

当前 `database/docker-compose.yml` 使用：

- PostgreSQL：`pgvector/pgvector:pg17`
- Redis：`redis:7-alpine`

如使用本机已有数据库，请确保 `backend/env/.env.dev` 中连接信息一致。

### 2. 启动后端

Windows 本地优先使用已有虚拟环境：

```powershell
cd backend
.\.venv3.13\Scripts\python.exe main.py run --env=dev
```

通用方式：

```bash
cd backend
uv sync
uv run main.py run --env=dev
```

或：

```bash
cd backend
pip install -r requirements.txt
python main.py run --env=dev
```

### 3. 同步权限、参数和内置数据

婚恋业务权限、菜单、岗位、角色授权、系统参数、CRM 内置渠道通过同一命令幂等补齐：

```powershell
cd backend
.\.venv3.13\Scripts\python.exe main.py sync-permissions --env=dev
```

通用方式：

```bash
cd backend
python main.py sync-permissions --env=dev
```

该命令会同步：

- 婚恋业务权限矩阵。
- 系统参数种子数据。
- 岗位种子数据。
- CRM 内置渠道：`MINIAPP_REGISTER`、`MANUAL_CREATE`、`IMPORT`、`EXTERNAL_PUSH`。
- CRM 渠道类型字典 `crm_channel_type`。

### 4. 启动管理后台

```bash
cd frontend
pnpm install
pnpm run dev
```

浏览器访问：

```txt
http://127.0.0.1:5180
```

## 常用命令

### 后端

```bash
cd backend
python main.py run --env=dev
python main.py revision --env=dev
python main.py upgrade --env=dev
python main.py sync-permissions --env=dev
python main.py backfill-service-workbench --env=dev
```

Windows 本地建议使用：

```powershell
cd backend
.\.venv3.13\Scripts\python.exe main.py sync-permissions --env=dev
```

Ruff 检查：

```bash
cd backend
uv run ruff check
uv run ruff check --fix
```

### 前端

```bash
cd frontend
pnpm install
pnpm run dev
pnpm run build
pnpm run type-check
pnpm run lint
```

已知：`pnpm run type-check` 可能失败在既有文件 `src/views/module_task/workflow/components/WorkflowDesignDrawer.vue` 的深层类型问题，和近期门店/权限文案改动无关。

## 后端开发约定

优先在 `backend/app/plugin/` 做业务二开，除非确实需要修改核心系统行为。

插件路由发现规则：

- 插件模块放在 `backend/app/plugin/` 下。
- 顶级插件目录命名为 `module_*`。
- 控制器文件命名为 `controller.py`。
- 每个 `controller.py` 定义一个或多个顶层 `APIRouter`。
- 从 `module_*` 到 `controller.py` 的目录都必须是合法 Python 包路径。
- 顶级目录会通过移除 `module_` 映射到 HTTP 路由前缀。

常见纵向切片结构：

```txt
controller.py  # HTTP 路由
service.py     # 业务逻辑
crud.py        # 数据访问
model.py       # SQLAlchemy ORM
schema.py      # Pydantic 模型
param.py       # 查询参数模型
```

控制器常用导入：

```python
from fastapi import APIRouter, Depends
from app.common.response import SuccessResponse
from app.core.router_class import OperationLogRoute
from app.core.dependencies import AuthPermission
from app.api.v1.module_system.auth.schema import AuthSchema
```

权限码需与菜单/按钮权限保持一致，例如：

```txt
crm:channel:query
crm:person:view_phone
crm:lead:sales:query
service:vip:assign
screen:device:bind
report:business:export_full
finance:payment:pay
```

## 前端开发约定

动态路由页面组件由以下规则解析：

```ts
import.meta.glob("../../views/**/**.vue")
```

新增业务页面通常需要同时补齐：

```txt
frontend/src/api/module_xxx/feature.ts
frontend/src/views/module_xxx/feature/index.vue
后端菜单数据：route_path / route_name / component_path / permission
```

常规路由示例：

```txt
route_path: /module_xxx/feature
component_path: module_xxx/feature/index
```

业务页面未实现前，菜单应保持隐藏或只作为权限占位，避免左侧菜单点击进入 404。

## 云支付口径

云支付配置统一放在「系统管理 - 参数管理」，配置键包括：

- `cloudpay.b_app_id`
- `cloudpay.private_key`
- `cloudpay.public_key`

交易接口前缀：

```txt
/api/v1/cloudpay/trade
```

包含：

- `/pay`
- `/precreate`
- `/create`
- `/query`
- `/refund`
- `/refund-query`

异步通知固定路径：

```txt
/api/v1/cloudpay/notify/trade
```

当前通知处理只做验签、日志记录并返回纯文本 `success`，暂不更新本地业务订单状态。

## 文档索引

- 后端说明：[backend/README.md](backend/README.md)
- 前端说明：[frontend/README.md](frontend/README.md)
- 云支付集成：[docs/云支付集成说明.md](docs/云支付集成说明.md)
- 婚恋小程序/智慧门店/CRM PRD：[docs/婚恋小程序-智慧门店大屏-CRM对接-PRD-v1.md](docs/婚恋小程序-智慧门店大屏-CRM对接-PRD-v1.md)

## 部署说明

当前后端镜像文件位于 [backend/Dockerfile](backend/Dockerfile)。[deploy.sh](deploy.sh) 仍保留原 FastApiAdmin 部署假设，和本项目当前结构不完全一致。正式生产部署前需要继续改造：

- 项目名与仓库地址改为当前系统。
- 由 MySQL 口径改为 PostgreSQL/pgvector 口径。
- 增加后端迁移和 `sync-permissions` 流程。
- 明确前端构建、静态资源、Nginx、后端容器和数据库容器编排方式。

当前根目录已提供基础 `docker-compose.yml`，只用于像启动 Redis 一样启动后端容器。PostgreSQL 和 Redis 仍按现有方式单独运行，后端容器默认通过 `host.docker.internal` 访问宿主机的 `5432` 和 `6379`：

```bash
docker compose up -d --build
```

查看状态和日志：

```bash
docker compose ps
docker compose logs -f backend
```

停止：

```bash
docker compose down
```

后端容器会挂载 `backend/env/.env.prod` 到容器内 `/app/env/.env.prod`。本地默认配置可以直接跑，生产环境必须修改数据库密码、Redis 密码、大模型密钥等配置。

后端镜像也可单独构建验证：

```bash
cd backend
docker build -t miailove-backend .
```

迁移和权限同步依赖数据库，不放在镜像构建阶段，应在部署流程中执行：

```bash
python main.py upgrade --env=prod
python main.py sync-permissions --env=prod
```

在部署脚本改造完成前，建议按 `database/`、`backend/`、`frontend/` 分别启动和验证。
