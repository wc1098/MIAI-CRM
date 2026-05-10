# 资源存储 - 阿里云 OSS

## 配置入口

资源存储配置统一维护在「系统管理 - 参数管理」。

当前种子参数：

| 参数键 | 默认值 | 说明 |
| --- | --- | --- |
| `storage.default_driver` | `aliyun_oss` | 资源上传默认存储驱动，可选 `local` / `aliyun_oss` |
| `storage.aliyun_oss.access_key_id` | 空 | 阿里云 OSS AccessKeyId |
| `storage.aliyun_oss.access_key_secret` | 空 | 阿里云 OSS AccessKeySecret |
| `storage.aliyun_oss.endpoint` | 空 | OSS Endpoint，例如 `https://oss-cn-hangzhou.aliyuncs.com` |
| `storage.aliyun_oss.bucket` | 空 | OSS Bucket 名称 |
| `storage.aliyun_oss.public_base_url` | 空 | 可选 CDN 或自定义域名 |
| `storage.aliyun_oss.object_prefix` | `uploads` | 上传对象 Key 前缀 |

## 同步命令

```bash
cd backend
python main.py sync-permissions --env=dev
```

该命令会幂等补齐系统参数。已在后台填写过的非空参数值不会被种子数据覆盖。

## 上传行为

现有文件上传入口保持不变：

- `module_common/file`
- `module_system/params` 中复用的上传能力

当 `storage.default_driver=aliyun_oss` 时，文件会上传到 OSS；当配置不完整时，接口会返回明确错误，提示到参数管理补充对应配置。

临时回退本地存储时，将 `storage.default_driver` 改为 `local`。
