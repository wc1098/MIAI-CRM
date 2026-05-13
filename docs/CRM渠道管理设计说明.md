# CRM渠道管理设计说明

## 口径

CRM渠道表示获客入口或数据来源入口，不表示注册后的业务动作。

- 小程序注册、人工录入、批量导入、外部系统推送属于渠道。
- 活动报名、认证支付、联系红娘属于后续来源事件。
- 名片分享注册归入小程序注册渠道，后续在来源事件中记录 `share_id`、来源用户、场景参数。

## 内置渠道

| 渠道编码 | 渠道名称 | 渠道类型 | 来源系统 |
| --- | --- | --- | --- |
| `MINIAPP_REGISTER` | 小程序注册 | `miniprogram` | `miniapp` |
| `MANUAL_CREATE` | 人工录入 | `manual` | `admin` |
| `IMPORT` | 批量导入 | `import` | `admin` |
| `EXTERNAL_PUSH` | 外部系统推送 | `external` | `external` |

内置渠道通过 `python main.py sync-permissions --env=dev` 幂等补齐。同步按 `channel_code` 匹配，不删除人工新增渠道，不覆盖人工维护的外部编码、落地页、描述。

## 字段说明

| 字段 | 说明 |
| --- | --- |
| `channel_code` | 渠道编码，全局唯一，允许字母、数字、下划线、中划线，长度 1-64 |
| `channel_name` | 渠道名称 |
| `channel_type` | 渠道类型：`miniprogram/manual/import/external/ad/offline/other` |
| `source_system` | 来源系统标识，预留外部系统对接 |
| `external_code` | 外部渠道编码，预留第三方映射 |
| `landing_url` | 落地页或投放页链接 |
| `sort` | 排序 |
| `status` | 状态，`0` 启用，`1` 停用 |
| `description` | 描述 |

## 菜单与权限

菜单位置：`CRM管理 > 渠道管理`。

接口前缀：`/api/v1/crm/channel`。

权限码：

- `crm:channel:query`
- `crm:channel:detail`
- `crm:channel:create`
- `crm:channel:update`
- `crm:channel:delete`
- `crm:channel:patch`
- `crm:channel:export`

默认授权：

- `ADMIN` 拥有全部权限。
- `HQ_OPS` 拥有渠道管理全部权限。
- 门店、销售、红娘、前台、大屏、审核、财务默认不授予渠道维护权限。

## 字典配置

渠道类型使用系统字典管理，字典类型为 `crm_channel_type`。默认字典项：

| 标签 | 值 |
| --- | --- |
| 小程序 | `miniprogram` |
| 人工录入 | `manual` |
| 批量导入 | `import` |
| 外部系统 | `external` |
| 广告投放 | `ad` |
| 线下渠道 | `offline` |
| 其他 | `other` |

后续新增抖音、信息流、私域、异业合作等类型时，在「系统管理 - 字典管理」维护 `crm_channel_type` 即可。

## 后续衔接

外部系统推送线索、来源事件、线索入池等能力后续开发时，应通过 `channel_code` 或 `external_code` 关联渠道。第一版不开放外部推送线索 API。
