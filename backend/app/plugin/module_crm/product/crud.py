from collections.abc import Sequence

from app.api.v1.module_system.auth.schema import AuthSchema
from app.core.base_crud import CRUDBase

from .model import CrmProductPackageModel
from .schema import ProductPackageCreateSchema, ProductPackageOutSchema, ProductPackageUpdateSchema


class ProductPackageCRUD(
    CRUDBase[CrmProductPackageModel, ProductPackageCreateSchema, ProductPackageUpdateSchema]
):
    """产品套餐数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        super().__init__(model=CrmProductPackageModel, auth=auth)

    async def get_by_id_crud(self, id: int) -> CrmProductPackageModel | None:
        return await self.get(id=id)

    async def get_by_name_crud(self, package_name: str) -> CrmProductPackageModel | None:
        return await self.get(package_name=package_name)

    async def list_crud(
        self,
        search: dict | None = None,
        order_by: list[dict] | None = None,
    ) -> Sequence[CrmProductPackageModel]:
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
            order_by=order_by or [{"sort": "asc"}, {"id": "desc"}],
            search=search or {},
            out_schema=ProductPackageOutSchema,
        )

    async def create_crud(self, data: ProductPackageCreateSchema) -> CrmProductPackageModel:
        return await self.create(data=data)

    async def update_crud(self, id: int, data: ProductPackageUpdateSchema) -> CrmProductPackageModel:
        return await self.update(id=id, data=data)

    async def delete_crud(self, ids: list[int]) -> None:
        await self.delete(ids=ids)

    async def set_status_crud(self, id: int, status: str) -> None:
        await self.set(ids=[id], status=status)
