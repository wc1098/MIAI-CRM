import json
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.dict.model import DictDataModel, DictTypeModel
from app.config.path_conf import SCRIPT_DIR
from app.plugin.module_crm.channel.model import CrmChannelModel
from app.plugin.module_crm.channel.schema import CHANNEL_CODE_PATTERN

CHANNEL_FILE = SCRIPT_DIR / "crm_channel.json"
CHANNEL_TYPE_DICT = {
    "dict_name": "CRM渠道类型",
    "dict_type": "crm_channel_type",
    "status": "0",
    "description": "CRM渠道类型列表",
}
CHANNEL_TYPE_DATA = [
    ("小程序", "miniprogram", 1),
    ("人工录入", "manual", 2),
    ("批量导入", "import", 3),
    ("外部系统", "external", 4),
    ("广告投放", "ad", 5),
    ("线下渠道", "offline", 6),
    ("其他", "other", 99),
]
LEAD_DICTS = [
    (
        {"dict_name": "CRM线索类型", "dict_type": "crm_lead_type", "status": "0", "description": "CRM线索类型列表"},
        [
            ("待分配", "pending", 1, "info"),
            ("新线索", "new", 2, "success"),
            ("二手线索", "second_hand", 3, "warning"),
            ("无效线索", "invalid", 4, "danger"),
            ("已转建档客户", "converted_customer", 5, "primary"),
        ],
    ),
    (
        {"dict_name": "CRM线索池类型", "dict_type": "crm_lead_pool_type", "status": "0", "description": "CRM线索池类型列表"},
        [("总部池", "hq_pool", 1, "info"), ("门店公海", "store_pool", 2, "warning"), ("销售私海", "sales_private", 3, "success")],
    ),
    (
        {"dict_name": "CRM跟进方式", "dict_type": "crm_follow_method", "status": "0", "description": "CRM跟进方式列表"},
        [("电话", "phone", 1, "primary"), ("微信", "wechat", 2, "success"), ("面谈", "meeting", 3, "warning"), ("其他", "other", 4, "info")],
    ),
    (
        {"dict_name": "CRM线索过程动作", "dict_type": "crm_lead_process_action", "status": "0", "description": "CRM线索过程动作列表"},
        [("普通跟进", "follow", 1, "primary"), ("标记无效", "invalid", 2, "danger"), ("释放", "release", 3, "warning"), ("转建档客户", "convert_customer", 4, "success")],
    ),
    (
        {"dict_name": "CRM婚况", "dict_type": "crm_marital_status", "status": "0", "description": "CRM婚况列表"},
        [("未婚", "single", 1, "primary"), ("离异", "divorced", 2, "warning"), ("丧偶", "widowed", 3, "info")],
    ),
    (
        {"dict_name": "CRM民族", "dict_type": "crm_ethnicity", "status": "0", "description": "CRM民族列表"},
        [
            ("汉族", "han", 1, "primary"),
            ("蒙古族", "mongol", 2, "info"),
            ("回族", "hui", 3, "info"),
            ("藏族", "tibetan", 4, "info"),
            ("维吾尔族", "uyghur", 5, "info"),
            ("苗族", "miao", 6, "info"),
            ("彝族", "yi", 7, "info"),
            ("壮族", "zhuang", 8, "info"),
            ("满族", "manchu", 9, "info"),
            ("其他", "other", 99, "info"),
        ],
    ),
    (
        {"dict_name": "CRM学历", "dict_type": "crm_education", "status": "0", "description": "CRM学历列表"},
        [
            ("高中及以下", "high_school_or_below", 1, "info"),
            ("大专", "college", 2, "primary"),
            ("本科", "bachelor", 3, "success"),
            ("硕士", "master", 4, "warning"),
            ("博士及以上", "doctor_or_above", 5, "danger"),
        ],
    ),
    (
        {"dict_name": "CRM年收入", "dict_type": "crm_annual_income", "status": "0", "description": "CRM年收入列表"},
        [("10万以下", "below_100k", 1, "info"), ("10-20万", "100k_200k", 2, "primary"), ("20-50万", "200k_500k", 3, "success"), ("50万以上", "above_500k", 4, "warning")],
    ),
    (
        {"dict_name": "CRM房产信息", "dict_type": "crm_house_status", "status": "0", "description": "CRM房产信息列表"},
        [("无房", "none", 1, "info"), ("有房无贷", "owned", 2, "success"), ("有房有贷", "mortgage", 3, "warning"), ("与父母同住", "family", 4, "primary")],
    ),
    (
        {"dict_name": "CRM购车信息", "dict_type": "crm_car_status", "status": "0", "description": "CRM购车信息列表"},
        [("无车", "none", 1, "info"), ("有车无贷", "owned", 2, "success"), ("有车有贷", "loan", 3, "warning")],
    ),
]


def _load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.loads(f.read())


def validate_crm_channels() -> dict[str, int]:
    rows = _load_json(CHANNEL_FILE)
    channel_codes = [row["channel_code"] for row in rows]
    if len(channel_codes) != len(set(channel_codes)):
        raise ValueError("crm_channel.json contains duplicated channel_code values")
    for row in rows:
        if not CHANNEL_CODE_PATTERN.match(row["channel_code"]):
            raise ValueError(f"invalid crm channel code: {row['channel_code']}")
        if not row["channel_type"]:
            raise ValueError(f"empty crm channel type: {row['channel_code']}")
    return {"channels": len(channel_codes)}


async def sync_crm_channels(db: AsyncSession) -> dict[str, int]:
    stats = {
        "dict_types_created": 0,
        "dict_data_created": 0,
        "dict_data_updated": 0,
        "channels_created": 0,
        "channels_updated": 0,
        "channels_skipped": 0,
    }
    await _sync_channel_type_dict(db=db, stats=stats)
    for dict_type, rows in LEAD_DICTS:
        await _sync_dict(db=db, stats=stats, dict_type=dict_type, rows=rows)
    await _delete_stale_dict_values(
        db=db,
        dict_type="crm_education",
        values={"master_or_above"},
    )

    rows = _load_json(CHANNEL_FILE)
    result = await db.execute(select(CrmChannelModel))
    channels_by_code = {channel.channel_code: channel for channel in result.scalars().all()}

    for row in rows:
        channel = channels_by_code.get(row["channel_code"])
        if channel is None:
            channel = CrmChannelModel(**row)
            db.add(channel)
            await db.flush()
            channels_by_code[channel.channel_code] = channel
            stats["channels_created"] += 1
            continue

        changed = False
        for field in ("channel_name", "channel_type", "source_system", "sort", "status"):
            if getattr(channel, field) != row.get(field):
                setattr(channel, field, row.get(field))
                changed = True
        if channel.is_deleted:
            channel.is_deleted = False
            channel.deleted_time = None
            channel.deleted_id = None
            changed = True

        if changed:
            stats["channels_updated"] += 1
        else:
            stats["channels_skipped"] += 1

    await db.flush()
    return stats


async def _delete_stale_dict_values(db: AsyncSession, dict_type: str, values: set[str]) -> None:
    if not values:
        return
    await db.execute(
        delete(DictDataModel).where(
            DictDataModel.dict_type == dict_type,
            DictDataModel.dict_value.in_(values),
        )
    )


async def _sync_channel_type_dict(db: AsyncSession, stats: dict[str, int]) -> None:
    await _sync_dict(
        db=db,
        stats=stats,
        dict_type=CHANNEL_TYPE_DICT,
        rows=[(label, value, sort, None) for label, value, sort in CHANNEL_TYPE_DATA],
    )


async def _sync_dict(
    db: AsyncSession,
    stats: dict[str, int],
    dict_type: dict[str, str],
    rows: list[tuple[str, str, int, str | None]],
) -> None:
    result = await db.execute(
        select(DictTypeModel).where(DictTypeModel.dict_type == dict_type["dict_type"])
    )
    dict_type_model = result.scalars().first()
    if dict_type_model is None:
        dict_type_model = DictTypeModel(**dict_type)
        db.add(dict_type_model)
        await db.flush()
        stats["dict_types_created"] += 1

    result = await db.execute(
        select(DictDataModel).where(DictDataModel.dict_type == dict_type["dict_type"])
    )
    data_by_value = {item.dict_value: item for item in result.scalars().all()}

    for label, value, sort, list_class in rows:
        data = data_by_value.get(value)
        if data is None:
            db.add(
                DictDataModel(
                    dict_sort=sort,
                    dict_label=label,
                    dict_value=value,
                    dict_type=dict_type["dict_type"],
                    dict_type_id=dict_type_model.id,
                    css_class="",
                    list_class=list_class,
                    is_default=sort == 1,
                    status="0",
                    description=label,
                )
            )
            stats["dict_data_created"] += 1
            continue

        changed = False
        for field, field_value in (
            ("dict_label", label),
            ("dict_sort", sort),
            ("dict_type_id", dict_type_model.id),
            ("list_class", list_class),
            ("status", "0"),
        ):
            if getattr(data, field) != field_value:
                setattr(data, field, field_value)
                changed = True
        if changed:
            stats["dict_data_updated"] += 1

    await db.flush()
