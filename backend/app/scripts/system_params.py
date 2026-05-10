import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.params.model import ParamsModel
from app.config.path_conf import SCRIPT_DIR


PARAM_FILE = SCRIPT_DIR / "sys_param.json"


def _load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.loads(f.read())


async def sync_system_params(db: AsyncSession) -> dict[str, int]:
    """
    幂等同步系统参数种子数据。

    已存在参数按 config_key 匹配，只同步名称、类型、状态、描述和空值占位；
    如果运维已在后台填写了非空配置值，不覆盖人工配置。
    """
    stats = {
        "params_created": 0,
        "params_updated": 0,
        "params_skipped": 0,
    }

    rows = _load_json(PARAM_FILE)
    result = await db.execute(select(ParamsModel))
    params_by_key = {param.config_key: param for param in result.scalars().all()}

    for row in rows:
        param = params_by_key.get(row["config_key"])
        if param is None:
            param = ParamsModel(**row)
            db.add(param)
            await db.flush()
            params_by_key[param.config_key] = param
            stats["params_created"] += 1
            continue

        changed = False
        for field in ("config_name", "config_type", "status", "description"):
            if getattr(param, field) != row.get(field):
                setattr(param, field, row.get(field))
                changed = True

        if not param.config_value and row.get("config_value"):
            param.config_value = row["config_value"]
            changed = True

        if param.is_deleted:
            param.is_deleted = False
            param.deleted_time = None
            param.deleted_id = None
            changed = True

        if changed:
            stats["params_updated"] += 1
        else:
            stats["params_skipped"] += 1

    await db.flush()
    return stats


def validate_system_params() -> dict[str, int]:
    rows = _load_json(PARAM_FILE)
    keys = [row["config_key"] for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("sys_param.json contains duplicated config_key values")
    return {"params": len(keys)}
