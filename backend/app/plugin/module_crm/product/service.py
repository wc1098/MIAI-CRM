from sqlalchemy import func, or_, select

from app.api.v1.module_system.auth.schema import AuthSchema
from app.core.exceptions import CustomException

from .crud import ProductPackageCRUD
from .model import CrmProductPackageModel
from .schema import (
    ProductPackageChangeStatusSchema,
    ProductPackageCreateSchema,
    ProductPackageOutSchema,
    ProductPackageQueryParam,
    ProductPackageUpdateSchema,
)


class ProductPackageService:
    """产品套餐服务层"""

    @classmethod
    async def detail_service(cls, auth: AuthSchema, id: int) -> dict:
        obj = await ProductPackageCRUD(auth).get_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="产品套餐不存在")
        return ProductPackageOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def page_service(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search: ProductPackageQueryParam | None = None,
    ) -> dict:
        offset = (page_no - 1) * page_size
        conditions = [CrmProductPackageModel.is_deleted.is_(False)]
        if search and getattr(search, "status", None):
            conditions.append(CrmProductPackageModel.status == search.status[1])
        if search and search.keyword:
            like_value = f"%{search.keyword}%"
            conditions.append(
                or_(
                    CrmProductPackageModel.package_name.like(like_value),
                    CrmProductPackageModel.description.like(like_value),
                    CrmProductPackageModel.internal_remark.like(like_value),
                )
            )

        count_sql = select(func.count(CrmProductPackageModel.id)).where(*conditions)
        total = (await auth.db.execute(count_sql)).scalar() or 0
        sql = (
            select(CrmProductPackageModel)
            .where(*conditions)
            .order_by(CrmProductPackageModel.sort.asc(), CrmProductPackageModel.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await auth.db.execute(sql)
        items = [
            ProductPackageOutSchema.model_validate(obj).model_dump()
            for obj in result.scalars().all()
        ]
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": offset + page_size < total,
            "items": items,
        }

    @classmethod
    async def list_enabled_service(cls, auth: AuthSchema) -> list[dict]:
        obj_list = await ProductPackageCRUD(auth).list_crud(
            search={"status": "0"},
            order_by=[{"sort": "asc"}, {"id": "desc"}],
        )
        return [ProductPackageOutSchema.model_validate(obj).model_dump() for obj in obj_list]

    @classmethod
    async def create_service(cls, auth: AuthSchema, data: ProductPackageCreateSchema) -> dict:
        await cls._ensure_name_available(auth=auth, package_name=data.package_name)
        obj = await ProductPackageCRUD(auth).create_crud(data=data)
        return ProductPackageOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def update_service(cls, auth: AuthSchema, id: int, data: ProductPackageUpdateSchema) -> dict:
        obj = await ProductPackageCRUD(auth).get_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="更新失败，产品套餐不存在")
        await cls._ensure_name_available(auth=auth, package_name=data.package_name, exclude_id=id)
        obj = await ProductPackageCRUD(auth).update_crud(id=id, data=data)
        return ProductPackageOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def change_status_service(cls, auth: AuthSchema, id: int, data: ProductPackageChangeStatusSchema) -> None:
        obj = await ProductPackageCRUD(auth).get_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="状态修改失败，产品套餐不存在")
        await ProductPackageCRUD(auth).set_status_crud(id=id, status=data.status)

    @classmethod
    async def delete_service(cls, auth: AuthSchema, id: int) -> None:
        obj = await ProductPackageCRUD(auth).get_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="删除失败，产品套餐不存在")
        await ProductPackageCRUD(auth).delete_crud(ids=[id])

    @classmethod
    async def _ensure_name_available(
        cls,
        auth: AuthSchema,
        package_name: str,
        exclude_id: int | None = None,
    ) -> None:
        sql = select(CrmProductPackageModel).where(
            CrmProductPackageModel.is_deleted.is_(False),
            CrmProductPackageModel.package_name == package_name,
        )
        if exclude_id is not None:
            sql = sql.where(CrmProductPackageModel.id != exclude_id)
        result = await auth.db.execute(sql)
        if result.scalars().first():
            raise CustomException(msg="产品套餐名称已存在")
