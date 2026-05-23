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
        {"dict_name": "CRM客户过程记录类型", "dict_type": "crm_customer_process_record_type", "status": "0", "description": "CRM客户过程记录类型列表"},
        [
            ("普通跟进", "follow", 1, "primary"),
            ("邀约到店", "appointment", 2, "warning"),
            ("到店面谈", "consultation", 3, "success"),
            ("服务沟通", "service_communication", 20, "primary"),
            ("需求确认", "service_requirement_confirm", 21, "success"),
            ("推荐说明", "service_recommendation_explain", 22, "warning"),
            ("约见反馈", "service_meeting_feedback", 23, "primary"),
            ("续费沟通", "service_renewal_communication", 24, "success"),
            ("关单沟通", "service_close_communication", 25, "info"),
            ("其他", "other", 99, "info"),
        ],
    ),
    (
        {"dict_name": "统一时间轴来源", "dict_type": "unified_timeline_source", "status": "0", "description": "统一过程时间轴来源列表"},
        [
            ("线索", "lead", 1, "primary"),
            ("销售", "sales", 2, "success"),
            ("到店", "visit", 3, "warning"),
            ("合同", "contract", 4, "danger"),
            ("收款", "receipt", 5, "success"),
            ("服务", "service", 6, "primary"),
            ("系统", "system", 7, "info"),
        ],
    ),
    (
        {"dict_name": "CRM线索跟进常用语", "dict_type": "crm_lead_follow_phrase", "status": "0", "description": "CRM线索跟进常用语列表"},
        [
            ("已电话沟通，客户有初步意向。", "phone_interested", 1, "primary"),
            ("微信已添加，等待客户回复。", "wechat_waiting", 2, "success"),
            ("客户暂时不方便，约定下次联系。", "next_contact", 3, "warning"),
            ("客户无明确需求，后续观察。", "observe_later", 4, "info"),
        ],
    ),
    (
        {"dict_name": "CRM客户意向等级", "dict_type": "crm_customer_intention_level", "status": "0", "description": "CRM客户意向等级列表"},
        [("高", "high", 1, "success"), ("中", "medium", 2, "warning"), ("低", "low", 3, "info")],
    ),
    (
        {"dict_name": "CRM客户到访目的", "dict_type": "crm_customer_visit_purpose", "status": "0", "description": "CRM客户到访目的列表"},
        [
            ("资料完善", "profile", 1, "primary"),
            ("服务介绍", "service_intro", 2, "success"),
            ("面谈沟通", "consultation", 3, "warning"),
            ("签约沟通", "signing", 4, "danger"),
            ("服务沟通", "service_communication", 20, "primary"),
            ("资料补充", "service_profile_completion", 21, "success"),
            ("深访沟通", "service_deep_interview", 22, "warning"),
            ("续费沟通", "service_renewal", 23, "danger"),
            ("其他", "other", 99, "info"),
        ],
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
    (
        {"dict_name": "CRM VIP等级", "dict_type": "crm_vip_level", "status": "0", "description": "CRM VIP等级列表"},
        [("银", "silver", 1, "info"), ("金", "gold", 2, "warning"), ("铂金", "platinum", 3, "primary"), ("钻石", "diamond", 4, "success")],
    ),
    (
        {"dict_name": "CRM VIP服务状态", "dict_type": "crm_vip_status", "status": "0", "description": "CRM VIP服务状态列表"},
        [("待分配", "pending_assign", 1, "warning"), ("服务中", "serving", 2, "success"), ("已暂停", "paused", 3, "info"), ("已关单", "closed", 4, "danger"), ("已过期", "expired", 5, "danger")],
    ),
    (
        {"dict_name": "CRM合同状态", "dict_type": "crm_contract_status", "status": "0", "description": "CRM合同状态列表"},
        [("草稿", "draft", 1, "info"), ("已签", "signed", 2, "warning"), ("待审核", "pending_review", 3, "warning"), ("待收款", "pending_payment", 4, "primary"), ("已生效", "effective", 5, "success"), ("已到期", "expired", 6, "danger"), ("已作废", "voided", 7, "danger")],
    ),
    (
        {"dict_name": "CRM收款类型", "dict_type": "crm_contract_receipt_type", "status": "0", "description": "CRM收款类型列表"},
        [("首款", "deposit", 1, "warning"), ("全款", "full", 2, "success"), ("尾款", "final", 3, "primary"), ("补款", "additional", 4, "info"), ("退款登记", "refund", 5, "danger"), ("其他", "other", 99, "info")],
    ),
    (
        {"dict_name": "CRM支付方式", "dict_type": "crm_contract_pay_method", "status": "0", "description": "CRM支付方式列表"},
        [("待选择", "pending", 1, "warning"), ("支付宝", "alipay", 2, "primary"), ("微信", "wechat", 3, "success"), ("现金", "cash", 4, "info"), ("银行转账", "bank_transfer", 5, "warning")],
    ),
    (
        {"dict_name": "CRM收款状态", "dict_type": "crm_contract_receipt_status", "status": "0", "description": "CRM收款状态列表"},
        [("待复核", "pending", 1, "warning"), ("待支付", "pending_payment", 2, "warning"), ("已确认", "approved", 3, "success"), ("已驳回", "rejected", 4, "danger"), ("已作废", "voided", 5, "info"), ("已冲正", "reversed", 6, "danger"), ("退款登记", "refund_registered", 7, "danger")],
    ),
    (
        {"dict_name": "CRM支付场景", "dict_type": "crm_contract_payment_scene", "status": "0", "description": "CRM支付场景列表"},
        [("待选择", "pending", 1, "warning"), ("线下确认", "offline", 2, "info"), ("扫码支付", "qrcode", 3, "primary"), ("条码支付", "barcode", 4, "success"), ("冲正", "reverse", 5, "danger"), ("退款登记", "refund_register", 6, "danger")],
    ),
    (
        {"dict_name": "服务工单状态", "dict_type": "service_case_status", "status": "0", "description": "服务工单状态列表"},
        [("待分配", "pending_assign", 1, "warning"), ("服务中", "serving", 2, "success"), ("待关单审核", "pending_close_review", 3, "warning"), ("已关单", "closed", 4, "info"), ("已过期", "expired", 5, "danger"), ("已重开", "reopened", 6, "primary")],
    ),
    (
        {"dict_name": "服务池类型", "dict_type": "service_pool_type", "status": "0", "description": "服务池类型列表"},
        [("待分配", "pending_assign", 1, "warning"), ("红娘私有", "matchmaker_private", 2, "success"), ("服务公海", "service_public", 3, "primary"), ("已关单", "closed", 4, "info")],
    ),
    (
        {"dict_name": "服务权益类型", "dict_type": "service_entitlement_type", "status": "0", "description": "服务权益类型列表"},
        [("推荐", "recommendation", 1, "primary"), ("约见", "meeting", 2, "success"), ("课程", "course", 3, "warning")],
    ),
    (
        {"dict_name": "服务核销状态", "dict_type": "service_usage_status", "status": "0", "description": "服务核销状态列表"},
        [("有效", "active", 1, "success"), ("已作废", "void", 2, "danger"), ("已回滚", "rolled_back", 3, "warning")],
    ),
    (
        {"dict_name": "服务深访类型", "dict_type": "deep_interview_type", "status": "0", "description": "服务深访类型列表"},
        [("首次深访", "first", 1, "primary"), ("阶段深访", "stage", 2, "success"), ("结案深访", "closing", 3, "warning")],
    ),
    (
        {"dict_name": "关单审核状态", "dict_type": "close_review_status", "status": "0", "description": "关单审核状态列表"},
        [("未申请", "none", 1, "info"), ("待审核", "pending", 2, "warning"), ("已通过", "approved", 3, "success"), ("已驳回", "rejected", 4, "danger")],
    ),
    (
        {"dict_name": "备选库来源", "dict_type": "candidate_source_type", "status": "0", "description": "备选库来源列表"},
        [("本门店搜索加入", "store_search", 1, "primary"), ("红娘手动新增", "manual_create", 2, "success"), ("本门店审核加入", "store_review_join", 3, "warning"), ("品牌审核加入", "brand_review_join", 4, "success")],
    ),
    (
        {"dict_name": "候选发现范围", "dict_type": "candidate_search_scope", "status": "0", "description": "候选发现范围列表"},
        [("本门店", "store", 1, "primary"), ("品牌", "brand", 2, "success")],
    ),
    (
        {"dict_name": "备选加入申请状态", "dict_type": "candidate_join_request_status", "status": "0", "description": "备选库加入申请状态列表"},
        [("待审核", "pending", 1, "warning"), ("已通过", "approved", 2, "success"), ("已驳回", "rejected", 3, "danger"), ("已撤回", "withdrawn", 4, "info")],
    ),
    (
        {"dict_name": "备选私有标签", "dict_type": "candidate_private_tag", "status": "0", "description": "红娘备选库私有标签建议项"},
        [
            ("形象好", "good_appearance", 1, "success"),
            ("沟通顺畅", "good_communication", 2, "primary"),
            ("高学历", "high_education", 3, "warning"),
            ("高收入", "high_income", 4, "warning"),
            ("本地稳定", "local_stable", 5, "success"),
            ("适合约见", "meeting_ready", 6, "primary"),
            ("资料待补充", "profile_incomplete", 7, "info"),
        ],
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
    for dict_type, dict_rows in LEAD_DICTS:
        for label, value, sort, _ in dict_rows:
            if sort < 1:
                raise ValueError(
                    f"{dict_type['dict_type']} has invalid dict_sort: {value}={sort} ({label})"
                )
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
