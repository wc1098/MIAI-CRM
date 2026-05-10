import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import ValidationError

from app.plugin.module_cloudpay.trade.client import CloudPayClient
from app.plugin.module_cloudpay.trade.schema import CloudPayPaySchema


def test_build_sign_content_sorts_keys_and_skips_empty_values():
    params = {
        "version": "1.0",
        "sign": "ignored",
        "biz_content": "{\"out_order_no\":\"A001\"}",
        "empty": "",
        "b_app_id": "B001",
    }

    assert (
        CloudPayClient.build_sign_content(params)
        == 'b_app_id=B001&biz_content={"out_order_no":"A001"}&version=1.0'
    )


def test_build_sign_content_stringifies_nested_values_as_compact_json():
    params = {
        "code": "10000",
        "data": {"out_order_no": "A001", "cp_mid": "M001"},
        "method": "ant.antfin.eco.cloudpay.trade.query",
    }

    assert (
        CloudPayClient.build_sign_content(params)
        == 'code=10000&data={"out_order_no":"A001","cp_mid":"M001"}'
        "&method=ant.antfin.eco.cloudpay.trade.query"
    )


def test_sign_and_verify_round_trip():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    content = "b_app_id=B001&version=1.0"
    signature = CloudPayClient.sign(content, private_pem)

    assert CloudPayClient.verify(content, signature, public_pem) is True
    assert CloudPayClient.verify(content + "&x=1", signature, public_pem) is False


def test_pay_schema_accepts_valid_amount_and_order_no():
    data = CloudPayPaySchema(
        dept_id=2,
        out_order_no="ORDER_001",
        total_amount="199.00",
        auth_code="28763443825664394",
        subject="合同收款",
    )

    assert data.out_order_no == "ORDER_001"


@pytest.mark.parametrize("total_amount", ["-1", "1.001", "abc"])
def test_pay_schema_rejects_invalid_amount(total_amount):
    with pytest.raises(ValidationError):
        CloudPayPaySchema(
            dept_id=2,
            out_order_no="ORDER_001",
            total_amount=total_amount,
            auth_code="28763443825664394",
            subject="合同收款",
        )


def test_pay_schema_rejects_invalid_order_no():
    with pytest.raises(ValidationError):
        CloudPayPaySchema(
            dept_id=2,
            out_order_no="ORDER-001",
            total_amount="199.00",
            auth_code="28763443825664394",
            subject="合同收款",
        )
