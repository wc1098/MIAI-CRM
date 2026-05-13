# AGENTS.MD

## 项目概览

本仓库是基于 FastApiAdmin 的全栈后台管理平台，当前正在此基础上二开「单品牌多门店」婚恋 CRM、小程序、智慧门店大屏与活动互动能力。

- 后端：`backend/`，技术栈为 FastAPI、SQLAlchemy 2.x、Pydantic 2.x、Alembic、Redis、APScheduler、Uvicorn。
- 前端：`frontend/`，技术栈为 Vue 3、Vite、TypeScript、Element Plus、Pinia、Vue Router、Axios。
- 文档：`README.md`、`backend/README.md`、`frontend/README.md`、`docs/fastapiadmin.md`、`docs/婚恋小程序-智慧门店大屏-CRM对接-PRD-v1.md`。

默认开发端口：

- 前端：`http://127.0.0.1:5180`
- 后端：`http://127.0.0.1:8001`
- Swagger：`http://127.0.0.1:8001/docs`
- API 前缀：`/api/v1`

## 重要业务口径

- 当前产品按「单品牌多门店」设计，门店是经营与数据隔离的核心组织单元。
- FastapiAdmin 底层仍使用 `sys_dept` 作为组织表，但产品展示口径统一叫「门店」。
- 「部门管理」已改为「门店管理」；`部门名称/部门编码` 展示为 `门店名称/门店编码`。
- `sys_user.username` 是登录账号，和登录、查重、重置密码强相关，页面上应叫「账号」。
- `sys_user.name` 是展示姓名，不用于登录，页面上应叫「姓名」。
- 婚恋业务权限基座已接入 `sys_role/sys_menu/sys_role_menus`，同步入口为：

```bash
cd backend
python main.py sync-permissions --env=dev
```

- 当前 `module_miailove` 前端业务页面尚未实现，`/miailove/...` 菜单节点先作为隐藏权限占位；实现对应 Vue 页面后再逐个开放显示。
- 岗位种子数据来自 `backend/app/scripts/data/sys_position.json`，也由权限同步命令幂等补齐。
- 门店编码允许纯数字，长度为 1-32 位；支付场景会使用纯数字门店编码。
- 云支付商户 ID `cp_mid` 使用启用的最顶级门店编码，云支付门店 ID `cp_store_id` 使用本系统门店 `sys_dept.id`。

## 后端地图

重要后端文件：

- `backend/main.py`：Typer CLI 入口，包含 `run`、`revision`、`upgrade`、`sync-permissions`。
- `backend/app/scripts/init_app.py`：FastAPI 应用注册、生命周期、路由、中间件、静态文件、文档。
- `backend/app/scripts/initialize.py`：初始化数据库表与基础数据。
- `backend/app/scripts/permission_matrix.py`：权限矩阵、岗位、角色、菜单与角色授权的幂等同步逻辑。
- `backend/app/scripts/system_params.py`：系统参数种子数据的幂等同步逻辑。
- `backend/app/scripts/crm_channels.py`：CRM渠道内置数据的幂等同步逻辑。
- `backend/app/utils/upload_util.py`：统一上传入口，按参数管理中的资源存储驱动切换本地/阿里云 OSS。
- `backend/app/utils/storage_config.py`：从 `sys_param` 读取资源存储配置。
- `backend/app/plugin/module_cloudpay/`：云支付插件模块，包含交易接口与异步通知基座。
- `backend/app/plugin/module_crm/`：CRM业务插件模块，当前包含渠道管理基座。
- `backend/app/core/discover.py`：动态插件路由发现。
- `backend/app/core/dependencies.py`：DB/Redis 依赖、JWT 用户加载、RBAC 权限校验。
- `backend/app/core/permission.py`：框架数据权限过滤。
- `backend/app/common/response.py`：统一 API 响应。
- `backend/app/core/router_class.py`：操作日志路由类。

核心模块位于 `backend/app/api/v1/`：

- `module_system`：auth、user、role、menu、dept、dict、params、notice、log、tenant、position。
- `module_monitor`：cache、online、resource、server。
- `module_common`：file、health。
- `module_application`：portal。

插件和二开模块位于 `backend/app/plugin/`。

## 后端模块模式

业务模块按纵向切片组织，通常包含：

```txt
controller.py  # HTTP 路由处理
service.py     # 业务逻辑
crud.py        # 数据访问
model.py       # SQLAlchemy ORM 模型
schema.py      # Pydantic 请求/响应模型
param.py       # 可选查询参数模型
```

新增模块时优先跟随现有模块模式，不要轻易引入新的抽象风格。

## 后端插件路由规则

动态插件路由由 `backend/app/core/discover.py` 发现。

规则：

- 插件模块必须放在 `backend/app/plugin/` 下。
- 顶级插件目录必须命名为 `module_*`，例如 `module_example`。
- 控制器文件名必须是 `controller.py`。
- 每个 `controller.py` 应定义一个或多个顶层 `APIRouter`。
- 从 `module_*` 到 `controller.py` 的目录都应是合法 Python 包/import 路径。
- 顶级目录会通过移除 `module_` 映射到 HTTP 路由前缀。

示例：

- `backend/app/plugin/module_example/demo/controller.py` 映射到 `/example`。
- `backend/app/plugin/module_ai/chat/controller.py` 映射到 `/ai`。

控制器常用导入：

```python
from fastapi import APIRouter, Depends
from app.common.response import SuccessResponse
from app.core.router_class import OperationLogRoute
from app.core.dependencies import AuthPermission
from app.api.v1.module_system.auth.schema import AuthSchema
```

权限字符串通常使用：

```txt
module_xxx:feature:action
```

例如：

- `module_system:user:query`
- `module_example:demo:create`

婚恋业务新增权限已使用更贴近业务域的前缀，例如：

- `crm:person:view_phone`
- `crm:lead:sales:query`
- `service:vip:assign`
- `screen:device:bind`
- `report:business:export_full`
- `finance:payment:pay`
- `crm:channel:query`

云支付接口权限：

- 支付、预创建、小程序创建：`finance:payment:pay`
- 交易查询：`finance:payment:query`
- 退款、退款查询：`finance:payment:refund`

## 后端命令

从 `backend/` 目录执行：

当前 Windows 本地后端虚拟环境为 `backend/.venv3.13`，后端校验、脚本、迁移、服务启动优先使用：

```bash
.\.venv3.13\Scripts\python.exe
```

```bash
uv sync
uv run main.py run --env=dev
```

或者：

```bash
pip install -r requirements.txt
python main.py run --env=dev
```

权限矩阵、岗位、角色、菜单、角色授权及系统参数同步：

```bash
python main.py sync-permissions --env=dev
```

在本地 Windows 环境优先使用虚拟环境执行：

```bash
.\.venv3.13\Scripts\python.exe main.py sync-permissions --env=dev
```

该命令也会幂等补齐 CRM 内置渠道数据，内置渠道来自 `backend/app/scripts/data/crm_channel.json`。

数据库迁移只用于模型结构变更，首次启动通常不需要手动执行：

```bash
uv run main.py revision --env=dev
uv run main.py upgrade --env=dev
```

Ruff 配置位于 `backend/pyproject.toml`：

```bash
uv run ruff check
uv run ruff check --fix
```

## 前端地图

重要前端文件：

- `frontend/package.json`：脚本与依赖。
- `frontend/src/utils/request.ts`：Axios 实例、认证头注入、统一响应/错误处理。
- `frontend/src/router/index.ts`：静态路由。
- `frontend/src/store/modules/permission.store.ts`：动态菜单路由生成与组件解析。
- `frontend/src/store/modules/user.store.ts`：用户、会话、菜单状态。
- `frontend/src/api/`：接口封装。
- `frontend/src/views/`：页面组件。

前端动态路由解析页面组件使用：

```ts
import.meta.glob("../../views/**/**.vue")
```

因此后端菜单的 `component_path` 必须匹配 `frontend/src/views/` 下真实存在的 Vue 文件。业务页面未实现前，菜单应保持隐藏或只作为权限占位，避免左侧菜单点击后进入 404。

## 前端模块模式

新增业务页面通常需要同时处理：

```txt
frontend/src/api/module_xxx/feature.ts
frontend/src/views/module_xxx/feature/index.vue
后端菜单数据：route_path / route_name / component_path / permission
```

常规页面路由示例：

```txt
/module_xxx/feature
component_path: module_xxx/feature/index
```

Axios base URL 使用 `import.meta.env.VITE_APP_BASE_API`，开发代理/API 前缀应与后端 `ROOT_PATH=/api/v1` 对齐。

## 前端命令

从 `frontend/` 目录执行：

```bash
pnpm install
pnpm run dev
pnpm run build
```

常用检查：

```bash
pnpm run type-check
pnpm run lint
```

当前已知：`pnpm run type-check` 会失败在既有文件 `src/views/module_task/workflow/components/WorkflowDesignDrawer.vue:762` 的深层类型问题，和近期门店/权限文案改动无关。

## 开发注意事项

- 后续记忆/协作说明请使用中文记录。
- 后续开发统一使用 UTF-8 编码；新增/修改文本文件、中文文档、JSON、前后端源码均保持 UTF-8。
- 项目运行配置优先放在「系统管理 - 参数管理」中统一维护，对应种子数据在 `backend/app/scripts/data/sys_param.json`，增量补齐通过 `python main.py sync-permissions --env=dev` 执行。
- 资源存储默认使用阿里云 OSS，配置键统一使用 `storage.*` 前缀；如需临时回退本地存储，将 `storage.default_driver` 改为 `local`。
- 云支付配置统一放在参数管理，配置键为 `cloudpay.b_app_id`、`cloudpay.private_key`、`cloudpay.public_key`；`sys_param.config_value` 已扩容为 `Text` 以保存密钥。
- 微信小程序配置统一放在参数管理，配置键为 `miniprogram.wechat.app_id`、`miniprogram.wechat.app_secret`。
- 云支付交易接口前缀为 `/api/v1/cloudpay/trade`，包含 `/pay`、`/precreate`、`/create`、`/query`、`/refund`、`/refund-query`。
- 云支付异步通知固定路径为 `/api/v1/cloudpay/notify/trade`；当前只做验签、日志记录、返回纯文本 `success`，暂不更新本地业务订单状态。
- 云支付支付、预创建、小程序创建接口如果调用方未传 `notify_url`，后端会自动使用当前请求域名生成 `/api/v1/cloudpay/notify/trade` 并透传给云支付。
- CRM 渠道管理位于「CRM管理 > 渠道管理」，接口前缀 `/api/v1/crm/channel`，用于维护获客入口/数据来源入口；活动报名、认证支付、联系红娘等注册后动作不作为渠道，后续进入 `SourceEvent`。
- 当前内置 CRM 渠道为 `MINIAPP_REGISTER`、`MANUAL_CREATE`、`IMPORT`、`EXTERNAL_PUSH`。
- CRM 渠道类型使用系统字典 `crm_channel_type` 管理，不要在前后端硬编码为不可扩展枚举；默认字典项会随 `sync-permissions` 补齐。
- CRM 线索管理已确认口径：必填字段为手机号、姓名、性别；扩展字段包含微信号、出生日期、身高、民族、职业、年收入、婚况、学历、籍贯、常驻地、房产信息、购车信息、照片相册。
- CRM 线索菜单规划为「全量线索 / 门店公海 / 销售私海」；销售是否可见并领取门店公海由门店级配置控制，默认关闭。
- CRM 线索类型为待分配、新线索、二手线索、无效线索、已转建档客户；当前没有“重新激活”概念，释放或自动回上级库后重新分配即二手线索。
- CRM 线索领取或分配后默认 7 天没有跟进自动回门店公海；无效、释放、转建档客户都通过过程记录完成并写生命周期审计。
- CRM 线索联系方式规则：未在自己线索库中不能看到完整联系方式，只返回脱敏手机号/微信号；品牌管理员和门店管理员可批量模板导入，重复手机号跳过并返回失败原因。
- 建档客户模块下一阶段再细化；当前“转建档客户”只作为线索终态和过程动作。
- 本地 Alembic 如出现表已存在但版本未对齐，可先确认表结构已存在，再使用 `stamp` 对齐到对应 revision；本次本地库已对齐到 `20260512_1000`。Windows PowerShell 运行迁移前建议设置 `$env:PYTHONIOENCODING='utf-8'`。
- Alembic 模型自动发现需跳过 `.venv*` 目录，否则本地 `.venv3.13` 会被误扫进模型导入路径。
- 优先在 `backend/app/plugin/` 做二开业务，除非确实需要修改核心系统行为。
- 后端 API 保持现有统一响应结构。
- 受保护接口继续使用 `AuthPermission`，权限码必须与菜单/按钮权限保持一致。
- 保持纵向切片模块组织。
- 结构性模型变更使用 Alembic 迁移命令。
- 前端页面接口封装放在 `src/api/module_*`，页面放在 `src/views/module_*`。
- 动态路由要特别注意 `route_path`、`route_name`、`component_path` 与真实 Vue 文件一致。
- 不要回滚仓库里与当前任务无关的本地改动。
