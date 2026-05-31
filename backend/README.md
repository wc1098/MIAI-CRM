# 觅AI婚恋数字门店后端

`backend/` 是本项目后端工程，基于 FastAPIAdmin 框架继续二开，当前承担管理后台 API、CRM 业务、门店权限、云支付、智慧门店大屏、服务工作台等能力。

## 技术栈

| 类型 | 技术 |
| --- | --- |
| Web 框架 | FastAPI、Uvicorn |
| ORM | SQLAlchemy 2.x |
| 数据校验 | Pydantic 2.x |
| 数据库迁移 | Alembic |
| 数据库 | PostgreSQL，兼容保留 MySQL/SQLite 框架能力 |
| 缓存 | Redis |
| 任务调度 | APScheduler |
| CLI | Typer |

## 默认本地配置

默认开发环境配置文件为：

```txt
backend/env/.env.dev
```

当前本地常用配置：

| 配置 | 默认值 |
| --- | --- |
| `SERVER_HOST` | `localhost` |
| `SERVER_PORT` | `8000` |
| `ROOT_PATH` | `/api/v1` |
| `DATABASE_TYPE` | `postgres` |
| `DATABASE_PORT` | `5432` |
| `DATABASE_NAME` | `miaicrm` |
| `REDIS_PORT` | `6379` |

Swagger 默认访问：

```txt
http://127.0.0.1:8000/docs
```

## 目录结构

```txt
backend/
├── app/
│   ├── api/v1/                    # 框架内置 API 模块
│   │   ├── module_system/          # 系统管理：用户、角色、菜单、门店、字典、参数等
│   │   ├── module_monitor/         # 缓存、在线用户、资源、服务器监控
│   │   ├── module_common/          # 文件、健康检查
│   │   └── module_application/     # 应用门户等
│   ├── plugin/                     # 二开插件与业务模块
│   │   ├── module_cloudpay/         # 云支付
│   │   ├── module_crm/              # CRM 业务
│   │   ├── module_screen/           # 智慧门店大屏
│   │   └── module_service/          # 服务工作台
│   ├── core/                       # 数据库、依赖、权限、路由类、插件发现
│   ├── scripts/                    # 初始化、权限矩阵、参数、内置数据
│   ├── common/                     # 统一响应、枚举、常量
│   ├── config/                     # 配置加载
│   └── utils/                      # 上传、存储配置、工具函数
├── env/                            # 环境配置
├── logs/                           # 日志
├── static/                         # 静态资源和本地上传文件
├── tests/                          # 测试
├── main.py                         # Typer CLI 与应用入口
├── alembic.ini
├── pyproject.toml
└── requirements.txt
```

## 业务模块组织方式

业务模块按纵向切片组织，通常包含：

```txt
controller.py  # HTTP 路由处理
service.py     # 业务逻辑
crud.py        # 数据访问
model.py       # SQLAlchemy ORM 模型
schema.py      # Pydantic 请求/响应模型
param.py       # 可选查询参数模型
```

新增模块优先跟随现有模块模式，不轻易引入新的抽象风格。

## 插件路由规则

动态插件路由由 `app/core/discover.py` 发现。

规则：

- 插件模块必须放在 `backend/app/plugin/` 下。
- 顶级插件目录必须命名为 `module_*`，例如 `module_crm`。
- 控制器文件名必须是 `controller.py`。
- 每个 `controller.py` 应定义一个或多个顶层 `APIRouter`。
- 从 `module_*` 到 `controller.py` 的目录都应是合法 Python 包/import 路径。
- 顶级目录会通过移除 `module_` 映射到 HTTP 路由前缀。

示例：

```txt
backend/app/plugin/module_cloudpay/trade/controller.py -> /cloudpay
backend/app/plugin/module_crm/channel/controller.py -> /crm
```

控制器常用导入：

```python
from fastapi import APIRouter, Depends
from app.common.response import SuccessResponse
from app.core.router_class import OperationLogRoute
from app.core.dependencies import AuthPermission
from app.api.v1.module_system.auth.schema import AuthSchema
```

## 常用命令

Windows 本地优先使用已有虚拟环境：

```powershell
cd backend
.\.venv3.13\Scripts\python.exe main.py run --env=dev
```

通用启动：

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

数据库迁移：

```bash
cd backend
python main.py revision --env=dev
python main.py upgrade --env=dev
```

生产环境示例：

```bash
cd backend
python main.py upgrade --env=prod
python main.py sync-permissions --env=prod
python main.py run --env=prod
```

## Docker 镜像

后端镜像文件位于：

```txt
backend/Dockerfile
```

从后端目录构建：

```bash
cd backend
docker build -t miailove-backend .
```

容器默认执行：

```bash
python main.py run --env=prod
```

镜像使用 `python:3.13-slim`，与当前本地 `backend/.venv3.13` 开发环境保持一致，减少开发环境和容器运行环境差异。

迁移和权限同步不放在 Dockerfile 构建阶段，应在部署流程或 compose 初始化步骤中执行：

```bash
python main.py upgrade --env=prod
python main.py sync-permissions --env=prod
```

生产运行时需要提供 `backend/env/.env.prod`，或通过容器环境变量注入数据库、Redis、密钥等配置。

## Docker Compose

根目录 `docker-compose.yml` 只编排后端服务：

- `backend`：基于 `backend/Dockerfile` 构建

PostgreSQL 和 Redis 仍按现有方式单独运行。后端容器默认通过 `host.docker.internal` 访问宿主机的 `5432` 和 `6379`。

从仓库根目录启动：

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

后端容器会挂载：

```txt
backend/env/.env.prod -> /app/env/.env.prod
```

因此本地运行前请确认 `backend/env/.env.prod` 存在。该文件已被 `.gitignore` 排除，生产部署时需要按实际密码和密钥修改。

## 权限、参数和内置数据同步

婚恋业务权限基座通过以下命令幂等同步：

```powershell
cd backend
.\.venv3.13\Scripts\python.exe main.py sync-permissions --env=dev
```

该命令会执行：

- 权限矩阵静态校验。
- 系统参数静态校验。
- CRM 渠道静态校验。
- 菜单、角色、岗位、角色授权同步。
- 系统参数同步。
- CRM 内置渠道同步。

内置岗位数据来自：

```txt
backend/app/scripts/data/sys_position.json
```

CRM 内置渠道数据来自：

```txt
backend/app/scripts/data/crm_channel.json
```

## 当前关键业务权限

```txt
crm:person:view_phone
crm:lead:sales:query
service:vip:assign
screen:device:bind
report:business:export_full
finance:payment:pay
finance:payment:query
finance:payment:refund
crm:channel:query
```

受保护接口继续使用 `AuthPermission`，权限码必须与菜单/按钮权限保持一致。

## 云支付

云支付模块位于：

```txt
backend/app/plugin/module_cloudpay/
```

交易接口前缀：

```txt
/api/v1/cloudpay/trade
```

接口：

- `/pay`
- `/precreate`
- `/create`
- `/query`
- `/refund`
- `/refund-query`

异步通知：

```txt
/api/v1/cloudpay/notify/trade
```

云支付配置统一放在系统参数：

```txt
cloudpay.b_app_id
cloudpay.private_key
cloudpay.public_key
```

支付、预创建、小程序创建接口如果调用方未传 `notify_url`，后端会自动使用当前请求域名生成 `/api/v1/cloudpay/notify/trade` 并透传给云支付。

## 资源存储

统一上传入口：

```txt
backend/app/utils/upload_util.py
```

资源存储配置读取：

```txt
backend/app/utils/storage_config.py
```

配置统一放在系统参数，键名使用 `storage.*` 前缀。默认使用阿里云 OSS；如需临时回退本地存储，将 `storage.default_driver` 改为 `local`。

## PostgreSQL 与 Alembic 注意事项

- 本地 Alembic 如出现表已存在但版本未对齐，可先确认表结构已存在，再使用 `stamp` 对齐到对应 revision。
- 当前本地库曾对齐到 `20260512_1000`。
- Windows PowerShell 运行迁移前建议设置：

```powershell
$env:PYTHONIOENCODING='utf-8'
```

- Alembic 模型自动发现需跳过 `.venv*` 目录，否则本地 `.venv3.13` 会被误扫进模型导入路径。

## 代码检查

Ruff 配置位于 `backend/pyproject.toml`。

```bash
cd backend
uv run ruff check
uv run ruff check --fix
```

## 开发原则

- 优先在 `backend/app/plugin/` 做二开业务。
- 后端 API 保持现有统一响应结构。
- 结构性模型变更使用 Alembic 迁移。
- 保持纵向切片模块组织。
- 新增接口按需接入操作日志和权限校验。
- 不要回滚与当前任务无关的本地改动。
