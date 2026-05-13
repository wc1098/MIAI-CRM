import os
from typing import Annotated

import typer
import uvicorn
from alembic import command
from alembic.config import Config
from fastapi import FastAPI

from app.common.enums import EnvironmentEnum

fastapiadmin_cli = typer.Typer()
alembic_cfg = Config("alembic.ini")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例并完成日志、中间件、路由与静态资源注册。

    返回:
    - FastAPI: 已配置生命周期的应用对象。
    """
    from app.config.setting import settings
    from app.scripts.init_app import (
        lifespan,
        register_exceptions,
        register_files,
        register_middlewares,
        register_routers,
        reset_api_docs,
    )

    # 创建FastAPI应用
    app = FastAPI(**settings.FASTAPI_CONFIG, lifespan=lifespan)

    from app.core.logger import setup_logging

    # 初始化日志
    setup_logging()
    # 注册各种组件
    register_exceptions(app)
    # 注册中间件
    register_middlewares(app)
    # 注册路由
    register_routers(app)
    # 注册静态文件
    register_files(app)
    # 重设API文档
    reset_api_docs(app)

    return app


# typer.Option是非必填；typer.Argument是必填
@fastapiadmin_cli.command(
    name="run",
    help="启动 FastapiAdmin 服务, 运行 python main.py run --env=dev 不加参数默认 dev 环境",
)
def run(
    env: Annotated[
        EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")
    ] = EnvironmentEnum.DEV,
) -> None:
    """
    按指定环境加载配置并启动 Uvicorn（开发环境开启 reload）。

    参数:
    - env (EnvironmentEnum): 运行环境，对应 `--env`。

    返回:
    - None
    """

    try:
        # 设置环境变量
        os.environ["ENVIRONMENT"] = env.value
        typer.echo("项目启动中...")

        # 清除配置缓存，确保重新加载配置
        from app.config.setting import get_settings

        get_settings.cache_clear()
        settings = get_settings()

        from app.core.logger import setup_logging

        setup_logging()

        # 显示启动横幅
        from app.utils.banner import worship

        worship(env.value)

        # 启动uvicorn服务
        uvicorn.run(
            app="main:create_app",
            host=settings.SERVER_HOST,
            port=settings.SERVER_PORT,
            reload=env.value == EnvironmentEnum.DEV.value,
            factory=True,
            log_config=None,
        )
    finally:
        from app.core.logger import cleanup_logging

        cleanup_logging()


@fastapiadmin_cli.command(
    name="revision",
    help="生成新的 Alembic 迁移脚本, 运行 python main.py revision --env=dev",
)
def revision(
    env: Annotated[
        EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")
    ] = EnvironmentEnum.DEV,
) -> None:
    """
    使用 Alembic 自动生成迁移脚本（autogenerate）。

    参数:
    - env (EnvironmentEnum): 运行环境，用于加载对应数据库模型元数据。

    返回:
    - None
    """
    os.environ["ENVIRONMENT"] = env.value
    from app.config.setting import get_settings

    get_settings.cache_clear()
    command.revision(alembic_cfg, autogenerate=True, message="迁移脚本")
    typer.echo("迁移脚本已生成")


@fastapiadmin_cli.command(
    name="upgrade",
    help="应用最新的 Alembic 迁移, 运行 python main.py upgrade --env=dev",
)
def upgrade(
    env: Annotated[
        EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")
    ] = EnvironmentEnum.DEV,
) -> None:
    """
    将数据库升级到 Alembic 最新版本（head）。

    参数:
    - env (EnvironmentEnum): 运行环境。

    返回:
    - None
    """
    os.environ["ENVIRONMENT"] = env.value
    from app.config.setting import get_settings

    get_settings.cache_clear()
    command.upgrade(alembic_cfg, "head")
    typer.echo("所有迁移已应用。")


@fastapiadmin_cli.command(
    name="sync-permissions",
    help="同步婚恋业务权限矩阵、系统参数和CRM渠道, 运行 python main.py sync-permissions --env=dev",
)
def sync_permissions(
    env: Annotated[
        EnvironmentEnum, typer.Option("--env", help="运行环境 (dev, prod)")
    ] = EnvironmentEnum.DEV,
) -> None:
    """
    幂等同步角色、菜单、角色菜单授权、系统参数与CRM渠道。

    参数:
    - env (EnvironmentEnum): 运行环境。

    返回:
    - None
    """
    import asyncio

    os.environ["ENVIRONMENT"] = env.value
    from app.config.setting import get_settings
    from app.core.database import async_db_session
    from app.scripts.crm_channels import sync_crm_channels, validate_crm_channels
    from app.scripts.permission_matrix import (
        sync_permission_matrix,
        validate_permission_matrix,
    )
    from app.scripts.system_params import sync_system_params, validate_system_params

    get_settings.cache_clear()
    validate_stats = validate_permission_matrix()
    typer.echo(f"权限矩阵静态校验通过: {validate_stats}")
    param_validate_stats = validate_system_params()
    typer.echo(f"系统参数静态校验通过: {param_validate_stats}")
    channel_validate_stats = validate_crm_channels()
    typer.echo(f"CRM渠道静态校验通过: {channel_validate_stats}")

    async def _sync() -> None:
        async with async_db_session() as session:
            async with session.begin():
                stats = await sync_permission_matrix(session)
                typer.echo(f"权限矩阵同步完成: {stats}")
                param_stats = await sync_system_params(session)
                typer.echo(f"系统参数同步完成: {param_stats}")
                channel_stats = await sync_crm_channels(session)
                typer.echo(f"CRM渠道同步完成: {channel_stats}")

    asyncio.run(_sync())


if __name__ == "__main__":
    fastapiadmin_cli()
