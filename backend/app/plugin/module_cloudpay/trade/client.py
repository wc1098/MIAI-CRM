import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.config.setting import settings
from app.core.exceptions import CustomException
from app.core.logger import log
from app.utils.storage_config import StorageConfig

CLOUDPAY_B_APP_ID = "cloudpay.b_app_id"
CLOUDPAY_PRIVATE_KEY = "cloudpay.private_key"
CLOUDPAY_PUBLIC_KEY = "cloudpay.public_key"
CLOUDPAY_GATEWAY = "https://ecogateway.alipay-eco.com/gateway.do"
CLOUDPAY_VERSION = "1.0"
CLOUDPAY_CHARSET = "UTF-8"
CLOUDPAY_SIGN_TYPE = "RSA2"


@dataclass(frozen=True)
class CloudPayConfig:
    b_app_id: str
    private_key: str
    public_key: str

    @property
    def missing_fields(self) -> list[str]:
        fields = {
            CLOUDPAY_B_APP_ID: self.b_app_id,
            CLOUDPAY_PRIVATE_KEY: self.private_key,
            CLOUDPAY_PUBLIC_KEY: self.public_key,
        }
        return [key for key, value in fields.items() if not value]


class CloudPayClient:
    """
    云支付公共请求客户端。
    """

    @staticmethod
    def dumps_biz_content(data: dict[str, Any]) -> str:
        cleaned = {k: v for k, v in data.items() if v is not None and v != ""}
        return json.dumps(cleaned, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _stringify_sign_value(value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return str(value)

    @classmethod
    def build_sign_content(cls, params: dict[str, Any]) -> str:
        parts = []
        for key in sorted(params.keys()):
            if key in {"sign", "signature"}:
                continue
            value = params[key]
            if value is None or value == "":
                continue
            parts.append(f"{key}={cls._stringify_sign_value(value)}")
        return "&".join(parts)

    @staticmethod
    def _normalize_private_key(key: str) -> bytes:
        value = key.strip().replace("\\n", "\n")
        if "BEGIN" not in value:
            value = f"-----BEGIN PRIVATE KEY-----\n{value}\n-----END PRIVATE KEY-----"
        return value.encode("utf-8")

    @staticmethod
    def _normalize_public_key(key: str) -> bytes:
        value = key.strip().replace("\\n", "\n")
        if "BEGIN" not in value:
            value = f"-----BEGIN PUBLIC KEY-----\n{value}\n-----END PUBLIC KEY-----"
        return value.encode("utf-8")

    @classmethod
    async def get_config(cls) -> CloudPayConfig:
        values = await StorageConfig.get_values(
            [CLOUDPAY_B_APP_ID, CLOUDPAY_PRIVATE_KEY, CLOUDPAY_PUBLIC_KEY]
        )
        config = CloudPayConfig(
            b_app_id=values.get(CLOUDPAY_B_APP_ID, "").strip(),
            private_key=values.get(CLOUDPAY_PRIVATE_KEY, "").strip(),
            public_key=values.get(CLOUDPAY_PUBLIC_KEY, "").strip(),
        )
        missing_fields = config.missing_fields
        if missing_fields:
            raise CustomException(msg=f"请在参数管理补充云支付配置: {', '.join(missing_fields)}")
        return config

    @classmethod
    def sign(cls, content: str, private_key: str) -> str:
        try:
            key = serialization.load_pem_private_key(
                cls._normalize_private_key(private_key),
                password=None,
            )
            signature = key.sign(
                content.encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return base64.b64encode(signature).decode("utf-8")
        except Exception as e:
            log.error(f"云支付签名失败: {e}")
            raise CustomException(msg=f"云支付签名失败: {e}") from e

    @classmethod
    def verify(cls, content: str, signature: str, public_key: str) -> bool:
        try:
            key = serialization.load_pem_public_key(cls._normalize_public_key(public_key))
            key.verify(
                base64.b64decode(signature),
                content.encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except Exception:
            return False

    @classmethod
    async def verify_response_payload(cls, payload: dict[str, Any], signature: str | None = None) -> bool:
        config = await cls.get_config()
        signature = signature or payload.get("sign") or payload.get("signature")
        if not signature:
            raise CustomException(msg="云支付通知缺少签名")
        sign_content = cls.build_sign_content(payload)
        if not cls.verify(sign_content, signature, config.public_key):
            raise CustomException(msg="云支付通知验签失败", data=payload)
        return True

    @classmethod
    async def execute(cls, method: str, biz_content: dict[str, Any]) -> dict[str, Any]:
        config = await cls.get_config()
        payload = {
            "b_app_id": config.b_app_id,
            "version": CLOUDPAY_VERSION,
            "method": method,
            "req_id": uuid4().hex,
            "charset": CLOUDPAY_CHARSET,
            "biz_content": cls.dumps_biz_content(biz_content),
            "timestamp": datetime.now().strftime("%Y%m%d%H%M%S"),
            "sign_type": CLOUDPAY_SIGN_TYPE,
        }
        payload["sign"] = cls.sign(cls.build_sign_content(payload), config.private_key)

        try:
            async with httpx.AsyncClient(timeout=settings.HTTPX_DEFAULT_TIMEOUT) as client:
                response = await client.post(CLOUDPAY_GATEWAY, json=payload)
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPError as e:
            log.error(f"云支付网关请求失败: {e}")
            raise CustomException(msg=f"云支付网关请求失败: {e}") from e
        except ValueError as e:
            log.error(f"云支付响应不是合法JSON: {e}")
            raise CustomException(msg="云支付响应不是合法JSON") from e

        if isinstance(result, dict) and result.get("sign"):
            result["sign_valid"] = await cls.verify_response_payload(result)

        if not isinstance(result, dict):
            raise CustomException(msg="云支付响应格式错误")
        if result.get("code") != "10000":
            error_msg = result.get("sub_msg") or result.get("msg") or "云支付业务失败"
            raise CustomException(msg=f"云支付业务失败: {error_msg}", data=result)
        return result
