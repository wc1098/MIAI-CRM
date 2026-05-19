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
        {"dict_name": "CRM职业", "dict_type": "crm_occupation", "status": "0", "description": "CRM职业列表"},
        [
            ("互联网/IT", "internet_it", 1, "primary"),
            ("金融/保险", "finance_insurance", 2, "success"),
            ("教育/培训", "education_training", 3, "warning"),
            ("医疗/护理", "medical_nursing", 4, "danger"),
            ("公务员/行政", "civil_admin", 5, "info"),
            ("自主创业", "entrepreneur", 6, "success"),
        ],
    ),
    (
        {"dict_name": "CRM单位类型", "dict_type": "crm_unit_type", "status": "0", "description": "CRM单位类型列表"},
        [
            ("国家机关", "government", 1, "primary"),
            ("事业单位", "public_institution", 2, "success"),
            ("国有企业", "state_owned", 3, "warning"),
            ("私营企业", "private", 4, "info"),
            ("外资企业", "foreign", 5, "danger"),
            ("自主创业", "entrepreneur", 6, "success"),
        ],
    ),
    (
        {"dict_name": "CRM结婚计划", "dict_type": "crm_marriage_plan", "status": "0", "description": "CRM结婚计划列表"},
        [("1年内", "within_1_year", 1, "success"), ("2年内", "within_2_years", 2, "primary"), ("看缘分", "depends", 3, "info")],
    ),
    (
        {"dict_name": "CRM房产信息", "dict_type": "crm_house_status", "status": "0", "description": "CRM房产信息列表"},
        [("无房", "none", 1, "info"), ("有房无贷", "owned", 2, "success"), ("有房有贷", "mortgage", 3, "warning"), ("与父母同住", "family", 4, "primary")],
    ),
    (
        {"dict_name": "CRM购车信息", "dict_type": "crm_car_status", "status": "0", "description": "CRM购车信息列表"},
        [("无车", "none", 1, "info"), ("有车无贷", "owned", 2, "success"), ("有车有贷", "loan", 3, "warning")],
    ),
    (
        {"dict_name": "CRM客户阶段", "dict_type": "crm_customer_stage", "status": "0", "description": "CRM客户阶段列表"},
        [
            ("建档完善", "profiling", 1, "info"),
            ("跟进经营", "following", 2, "primary"),
            ("已邀约", "appointed", 3, "warning"),
            ("已到店", "visited", 4, "success"),
            ("已面谈", "consulted", 5, "success"),
            ("签约推进", "signing", 6, "warning"),
            ("已签约待付款", "contracted", 7, "primary"),
            ("已转VIP", "converted_vip", 8, "success"),
        ],
    ),
    (
        {"dict_name": "CRM客户退回原因", "dict_type": "crm_customer_return_reason", "status": "0", "description": "CRM客户退回原因列表"},
        [
            ("无效客户", "invalid", 1, "danger"),
            ("长期未响应", "no_response", 2, "warning"),
            ("暂缓考虑", "not_ready", 3, "info"),
            ("预算不符", "budget_mismatch", 4, "warning"),
            ("需求不匹配", "requirement_mismatch", 5, "warning"),
            ("重复建档", "duplicate", 6, "info"),
            ("客户明确拒绝", "rejected", 7, "danger"),
            ("其他", "other", 99, "info"),
        ],
    ),
    (
        {"dict_name": "CRM客户跟进方式", "dict_type": "crm_customer_follow_method", "status": "0", "description": "CRM客户跟进方式列表"},
        [("电话", "phone", 1, "primary"), ("微信", "wechat", 2, "success"), ("邀约", "appointment", 3, "warning"), ("面谈", "consultation", 4, "danger")],
    ),
    (
        {"dict_name": "CRM客户跟进常用语", "dict_type": "crm_customer_follow_phrase", "status": "0", "description": "CRM客户跟进常用语列表"},
        [
            ("已电话沟通，客户有初步意向。", "phone_interested", 1, "primary"),
            ("已微信沟通，等待客户进一步回复。", "wechat_waiting", 2, "success"),
            ("客户暂时不方便，已约定下次联系。", "next_contact", 3, "warning"),
            ("客户对服务感兴趣，可继续推进邀约。", "push_appointment", 4, "success"),
        ],
    ),
    (
        {"dict_name": "CRM客户意向等级", "dict_type": "crm_customer_intention_level", "status": "0", "description": "CRM客户意向等级列表"},
        [("高", "high", 1, "success"), ("中", "medium", 2, "warning"), ("低", "low", 3, "info")],
    ),
    (
        {"dict_name": "CRM客户到访目的", "dict_type": "crm_customer_visit_purpose", "status": "0", "description": "CRM客户到访目的列表"},
        [("资料完善", "profile", 1, "primary"), ("服务介绍", "service_intro", 2, "success"), ("面谈沟通", "consultation", 3, "warning"), ("签约沟通", "signing", 4, "danger")],
    ),
    (
        {"dict_name": "CRM客户预约时段", "dict_type": "crm_customer_appointment_slot", "status": "0", "description": "CRM客户预约时段列表"},
        [
            ("8:00-10:00", "08_10", 1, "info"),
            ("10:00-12:00", "10_12", 2, "info"),
            ("12:00-14:00", "12_14", 3, "info"),
            ("14:00-16:00", "14_16", 4, "primary"),
            ("16:00-18:00", "16_18", 5, "primary"),
            ("18:00-20:00", "18_20", 6, "warning"),
            ("20:00-21:00", "20_21", 7, "warning"),
        ],
    ),
    (
        {"dict_name": "CRM客户预约状态", "dict_type": "crm_customer_appointment_status", "status": "0", "description": "CRM客户预约状态列表"},
        [("待到访", "pending", 1, "warning"), ("已到店", "checked_in", 2, "success"), ("已面谈", "consulted", 3, "primary"), ("已爽约", "no_show", 4, "danger"), ("已取消", "cancelled", 5, "info")],
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
