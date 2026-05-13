from collections.abc import Sequence

from app.api.v1.module_system.auth.schema import AuthSchema
from app.core.base_crud import CRUDBase

from .model import CrmChannelModel
from .schema import ChannelCreateSchema, ChannelOutSchema, ChannelUpdateSchema


class ChannelCRUD(CRUDBase[CrmChannelModel, ChannelCreateSchema, ChannelUpdateSchema]):
    """渠道数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        super().__init__(model=CrmChannelModel, auth=auth)

    async def get_by_id_crud(self, id: int) -> CrmChannelModel | None:
        return await self.get(id=id)

    async def list_crud(
        self,
        search: dict | None = None,
        order_by: list[dict] | None = None,
    ) -> Sequence[CrmChannelModel]:
        return await self.list(search=search, order_by=order_by)

    async def page_crud(
        self,
        offset: int,
        limit: int,
        order_by: list[dict] | None = None,
        search: dict | None = None,
    ) -> dict:
        return await self.page(
            offset=offset,
            limit=limit,
            order_by=order_by or [{"sort": "asc"}, {"id": "asc"}],
            search=search or {},
            out_schema=ChannelOutSchema,
        )

    async def create_crud(self, data: ChannelCreateSchema) -> CrmChannelModel:
        return await self.create(data=data)

    async def update_crud(self, id: int, data: ChannelUpdateSchema) -> CrmChannelModel:
        return await self.update(id=id, data=data)

    async def delete_crud(self, ids: list[int]) -> None:
        await self.delete(ids=ids)

    async def set_available_crud(self, ids: list[int], status: str) -> None:
        await self.set(ids=ids, status=status)
