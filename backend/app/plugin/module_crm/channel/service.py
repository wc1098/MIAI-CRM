from typing import Any

from app.api.v1.module_system.auth.schema import AuthSchema
from app.core.base_schema import BatchSetAvailable
from app.core.exceptions import CustomException
from app.utils.excel_util import ExcelUtil

from .crud import ChannelCRUD
from .schema import ChannelCreateSchema, ChannelOutSchema, ChannelQueryParam, ChannelUpdateSchema


class ChannelService:
    """渠道服务层"""

    @classmethod
    async def detail_service(cls, auth: AuthSchema, id: int) -> dict:
        obj = await ChannelCRUD(auth).get_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="渠道不存在")
        return ChannelOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def list_service(
        cls,
        auth: AuthSchema,
        search: ChannelQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> list[dict]:
        obj_list = await ChannelCRUD(auth).list_crud(
            search=search.__dict__ if search else {},
            order_by=order_by or [{"sort": "asc"}, {"id": "asc"}],
        )
        return [ChannelOutSchema.model_validate(obj).model_dump() for obj in obj_list]

    @classmethod
    async def page_service(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search: ChannelQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> dict:
        return await ChannelCRUD(auth).page_crud(
            offset=(page_no - 1) * page_size,
            limit=page_size,
            order_by=order_by or [{"sort": "asc"}, {"id": "asc"}],
            search=search.__dict__ if search else {},
        )

    @classmethod
    async def create_service(cls, auth: AuthSchema, data: ChannelCreateSchema) -> dict:
        exist_obj = await ChannelCRUD(auth).get(channel_code=data.channel_code)
        if exist_obj:
            raise CustomException(msg="创建失败，渠道编码已存在")
        obj = await ChannelCRUD(auth).create_crud(data=data)
        return ChannelOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def update_service(cls, auth: AuthSchema, id: int, data: ChannelUpdateSchema) -> dict:
        obj = await ChannelCRUD(auth).get_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="更新失败，渠道不存在")
        exist_obj = await ChannelCRUD(auth).get(channel_code=data.channel_code)
        if exist_obj and exist_obj.id != id:
            raise CustomException(msg="更新失败，渠道编码已存在")
        obj = await ChannelCRUD(auth).update_crud(id=id, data=data)
        return ChannelOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def delete_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        if len(ids) < 1:
            raise CustomException(msg="删除失败，删除对象不能为空")
        for id in ids:
            obj = await ChannelCRUD(auth).get_by_id_crud(id=id)
            if not obj:
                raise CustomException(msg=f"删除失败，ID为{id}的渠道不存在")
        await ChannelCRUD(auth).delete_crud(ids=ids)

    @classmethod
    async def set_available_service(cls, auth: AuthSchema, data: BatchSetAvailable) -> None:
        await ChannelCRUD(auth).set_available_crud(ids=data.ids, status=data.status)

    @classmethod
    async def export_service(cls, obj_list: list[dict[str, Any]]) -> bytes:
        mapping_dict = {
            "channel_code": "渠道编码",
            "channel_name": "渠道名称",
            "channel_type": "渠道类型",
            "source_system": "来源系统",
            "external_code": "外部渠道编码",
            "landing_url": "落地页",
            "sort": "排序",
            "status": "状态",
            "description": "描述",
            "created_time": "创建时间",
            "updated_time": "更新时间",
        }
        data = obj_list.copy()
        for item in data:
            item["status"] = "启用" if item.get("status") == "0" else "停用"
        return ExcelUtil.export_list2excel(list_data=data, mapping_dict=mapping_dict)
