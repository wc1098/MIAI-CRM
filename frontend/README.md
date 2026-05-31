# 觅AI婚恋数字门店管理后台

`frontend/` 是本项目管理后台前端工程，基于 Vue 3、Vite、TypeScript、Element Plus、Pinia、Vue Router 和 Axios 构建。

## 默认本地地址

| 项目 | 默认值 |
| --- | --- |
| 前端开发地址 | `http://127.0.0.1:5180` |
| 后端地址 | `http://127.0.0.1:8000` |
| API 前缀 | `/api/v1` |
| 配置文件 | `.env.development` |

实际配置以 `.env.development`、`.env.production` 为准。

## 目录结构

```txt
frontend/
├── public/                 # 静态资源
├── src/
│   ├── api/                # API 封装
│   ├── assets/             # 资源
│   ├── components/         # 通用组件
│   ├── constants/          # 常量
│   ├── layouts/            # 布局
│   ├── plugins/            # 插件
│   ├── router/             # 静态路由
│   ├── store/              # Pinia 状态
│   ├── styles/             # 样式
│   ├── types/              # 类型定义
│   ├── utils/              # 工具函数
│   └── views/              # 页面
├── .env.development
├── .env.production.example
├── package.json
├── pnpm-lock.yaml
├── tsconfig.json
├── uno.config.ts
└── vite.config.ts
```

## 快速启动

```bash
cd frontend
pnpm install
pnpm run dev
```

生产构建：

```bash
cd frontend
pnpm run build
```

常用检查：

```bash
cd frontend
pnpm run type-check
pnpm run lint
```

已知：`pnpm run type-check` 可能失败在既有文件 `src/views/module_task/workflow/components/WorkflowDesignDrawer.vue` 的深层类型问题，和近期门店/权限文案改动无关。

## 环境变量

开发环境配置：

```txt
frontend/.env.development
```

关键字段：

```txt
VITE_APP_ENV=development
VITE_APP_TITLE=fastapiadmin
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_APP_BASE_API=/api/v1
VITE_APP_PORT=5180
VITE_TIMEOUT=10000
VITE_APP_WS_ENDPOINT=ws://127.0.0.1:8000
```

后续可将 `VITE_APP_TITLE` 调整为当前产品名；部署时请同步调整 `.env.production`。

## 请求封装

Axios 实例位于：

```txt
frontend/src/utils/request.ts
```

接口文件统一放在：

```txt
frontend/src/api/
```

新增业务接口建议按模块组织：

```txt
frontend/src/api/module_xxx/feature.ts
```

## 路由与菜单

静态路由：

```txt
frontend/src/router/index.ts
```

动态菜单路由生成：

```txt
frontend/src/store/modules/permission.store.ts
```

页面组件解析使用：

```ts
import.meta.glob("../../views/**/**.vue")
```

因此后端菜单的 `component_path` 必须匹配 `frontend/src/views/` 下真实存在的 Vue 文件。

常规页面约定：

```txt
路由：/module_xxx/feature
页面：frontend/src/views/module_xxx/feature/index.vue
component_path：module_xxx/feature/index
API：frontend/src/api/module_xxx/feature.ts
```

业务页面未实现前，菜单应保持隐藏或只作为权限占位，避免左侧菜单点击后进入 404。

## 当前业务展示口径

- 「部门」统一展示为「门店」。
- 「部门管理」统一展示为「门店管理」。
- `sys_user.username` 展示为「账号」，用于登录、查重、重置密码。
- `sys_user.name` 展示为「姓名」，只用于人员展示。
- CRM 渠道管理位于「CRM管理 > 渠道管理」。
- 当前 `/miailove/...` 菜单节点可先作为隐藏权限占位，待页面实现后再开放显示。

## 新增页面流程

1. 在 `src/api/module_xxx/feature.ts` 增加接口封装。
2. 在 `src/views/module_xxx/feature/index.vue` 增加页面组件。
3. 确认后端菜单的 `route_path`、`route_name`、`component_path`、`permission` 与页面一致。
4. 执行 `backend` 的 `sync-permissions` 同步菜单和权限。
5. 登录后台验证菜单、按钮权限、接口权限和页面跳转。

## 开发注意事项

- 页面、接口和权限命名优先跟随后端业务域。
- 不要在前端硬编码 CRM 渠道类型，渠道类型来自系统字典 `crm_channel_type`。
- 前端只展示完整联系方式时应遵循后端返回结果，不自行拼接或绕过脱敏逻辑。
- 新增菜单前先保证真实 Vue 页面存在。
- Axios base URL 使用 `import.meta.env.VITE_APP_BASE_API`，开发代理/API 前缀需与后端 `ROOT_PATH=/api/v1` 对齐。
