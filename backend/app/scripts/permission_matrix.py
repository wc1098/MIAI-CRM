import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.menu.model import MenuModel
from app.api.v1.module_system.position.model import PositionModel
from app.api.v1.module_system.role.model import RoleMenusModel, RoleModel
from app.config.path_conf import SCRIPT_DIR


ROLE_FILE = SCRIPT_DIR / "sys_role.json"
MENU_FILE = SCRIPT_DIR / "sys_menu.json"
ROLE_MENU_FILE = SCRIPT_DIR / "sys_role_menu_permissions.json"
POSITION_FILE = SCRIPT_DIR / "sys_position.json"


def _load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.loads(f.read())


def _iter_menu_tree(
    nodes: list[dict[str, Any]], parent_key: str | None = None
) -> list[tuple[dict[str, Any], str, str | None]]:
    rows: list[tuple[dict[str, Any], str, str | None]] = []
    for node in nodes:
        if node.get("type") == 3:
            key = f"{parent_key or 'root'}::{node.get('permission') or node.get('title')}"
        else:
            key = node.get("route_path") or node.get("permission")
        if not key:
            key = f"{parent_key or 'root'}::{node.get('title') or node.get('name')}"
        rows.append((node, key, parent_key))
        rows.extend(_iter_menu_tree(node.get("children") or [], key))
    return rows


def _menu_payload(node: dict[str, Any], parent_id: int | None) -> dict[str, Any]:
    allowed = {
        "name",
        "type",
        "order",
        "permission",
        "icon",
        "route_name",
        "route_path",
        "component_path",
        "redirect",
        "hidden",
        "keep_alive",
        "always_show",
        "title",
        "params",
        "affix",
        "status",
        "description",
    }
    payload = {k: v for k, v in node.items() if k in allowed}
    payload["parent_id"] = parent_id
    return payload


async def sync_permission_matrix(db: AsyncSession) -> dict[str, int]:
    """
    Idempotently sync the role, menu, and default role-menu permission matrix.

    Existing rows are matched by role code and menu permission/route path. The sync adds
    missing role-menu grants but does not remove manual grants.
    """
    stats = {
        "positions_created": 0,
        "positions_updated": 0,
        "roles_created": 0,
        "roles_updated": 0,
        "menus_created": 0,
        "menus_updated": 0,
        "role_menus_created": 0,
        "role_menus_skipped": 0,
    }

    role_rows = _load_json(ROLE_FILE)
    position_rows = _load_json(POSITION_FILE)
    menu_rows = _load_json(MENU_FILE)
    role_menu_rows = _load_json(ROLE_MENU_FILE)

    position_result = await db.execute(select(PositionModel))
    positions_by_name = {position.name: position for position in position_result.scalars().all()}

    for row in position_rows:
        position = positions_by_name.get(row["name"])
        if position is None:
            position = PositionModel(**row)
            db.add(position)
            await db.flush()
            positions_by_name[position.name] = position
            stats["positions_created"] += 1
            continue

        changed = False
        for field in ("order", "status", "description"):
            if getattr(position, field) != row.get(field):
                setattr(position, field, row.get(field))
                changed = True
        if position.is_deleted:
            position.is_deleted = False
            position.deleted_time = None
            position.deleted_id = None
            changed = True
        if changed:
            stats["positions_updated"] += 1

    role_result = await db.execute(select(RoleModel))
    roles_by_code = {role.code: role for role in role_result.scalars().all()}

    for row in role_rows:
        role = roles_by_code.get(row["code"])
        if role is None:
            role = RoleModel(**row)
            db.add(role)
            await db.flush()
            roles_by_code[role.code] = role
            stats["roles_created"] += 1
            continue

        changed = False
        for field in ("name", "order", "data_scope", "status", "description"):
            if getattr(role, field) != row.get(field):
                setattr(role, field, row.get(field))
                changed = True
        if changed:
            stats["roles_updated"] += 1

    await db.flush()

    menu_result = await db.execute(select(MenuModel))
    menus = menu_result.scalars().all()
    menus_by_permission = {m.permission: m for m in menus if m.permission}
    menus_by_route = {m.route_path: m for m in menus if m.route_path}
    menus_by_key: dict[str, MenuModel] = {}
    menus_by_button_key = {
        (m.parent_id, m.permission, m.title): m
        for m in menus
        if m.type == 3 and m.permission
    }

    for node, key, _ in _iter_menu_tree(menu_rows):
        if node.get("type") == 3:
            continue
        existing = None
        if node.get("route_path"):
            existing = menus_by_route.get(node["route_path"])
        if existing is None and node.get("permission"):
            existing = menus_by_permission.get(node["permission"])
        if existing is not None:
            menus_by_key[key] = existing

    for node, key, parent_key in _iter_menu_tree(menu_rows):
        parent_id = menus_by_key[parent_key].id if parent_key else None
        payload = _menu_payload(node, parent_id)
        menu = menus_by_key.get(key)
        if menu is None and node.get("type") == 3:
            menu = menus_by_button_key.get((parent_id, node.get("permission"), node.get("title")))
        if menu is None:
            menu = MenuModel(**payload)
            db.add(menu)
            await db.flush()
            menus_by_key[key] = menu
            if menu.permission:
                menus_by_permission[menu.permission] = menu
            if menu.route_path:
                menus_by_route[menu.route_path] = menu
            if menu.type == 3 and menu.permission:
                menus_by_button_key[(menu.parent_id, menu.permission, menu.title)] = menu
            stats["menus_created"] += 1
            continue

        changed = False
        for field, value in payload.items():
            if getattr(menu, field) != value:
                setattr(menu, field, value)
                changed = True
        if changed:
            stats["menus_updated"] += 1

    await db.flush()

    menu_result = await db.execute(select(MenuModel))
    all_menus = menu_result.scalars().all()
    menus_by_permission: dict[str, list[MenuModel]] = {}
    for menu in all_menus:
        if menu.permission:
            menus_by_permission.setdefault(menu.permission, []).append(menu)
    parent_by_id = {m.id: m.parent_id for m in all_menus}
    all_menu_ids = {m.id for m in all_menus}

    existing_result = await db.execute(select(RoleMenusModel))
    existing_pairs = {
        (row.role_id, row.menu_id) for row in existing_result.scalars().all()
    }

    def with_ancestors(menu_ids: set[int]) -> set[int]:
        expanded = set(menu_ids)
        for menu_id in list(menu_ids):
            parent_id = parent_by_id.get(menu_id)
            while parent_id:
                expanded.add(parent_id)
                parent_id = parent_by_id.get(parent_id)
        return expanded

    for row in role_menu_rows:
        role = roles_by_code.get(row["role_code"])
        if role is None:
            continue
        permissions = row.get("permissions") or []
        if "*" in permissions:
            target_ids = set(all_menu_ids)
        else:
            target_ids = {
                menu.id
                for permission in permissions
                for menu in menus_by_permission.get(permission, [])
            }
        for menu_id in with_ancestors(target_ids):
            pair = (role.id, menu_id)
            if pair in existing_pairs:
                stats["role_menus_skipped"] += 1
                continue
            db.add(RoleMenusModel(role_id=role.id, menu_id=menu_id))
            existing_pairs.add(pair)
            stats["role_menus_created"] += 1

    await db.flush()
    return stats


def validate_permission_matrix() -> dict[str, int]:
    roles = _load_json(ROLE_FILE)
    positions = _load_json(POSITION_FILE)
    menus = _load_json(MENU_FILE)
    role_menus = _load_json(ROLE_MENU_FILE)

    role_codes = [role["code"] for role in roles]
    if len(role_codes) != len(set(role_codes)):
        raise ValueError("sys_role.json contains duplicated role code values")

    position_names = [position["name"] for position in positions]
    if len(position_names) != len(set(position_names)):
        raise ValueError("sys_position.json contains duplicated position names")

    permissions = [
        node["permission"]
        for node, _, _ in _iter_menu_tree(menus)
        if node.get("permission")
    ]
    permission_set = set(permissions)
    for row in role_menus:
        for permission in row.get("permissions") or []:
            if permission != "*" and permission not in permission_set:
                raise ValueError(
                    f"{row['role_code']} references unknown permission: {permission}"
                )

    return {
        "positions": len(position_names),
        "roles": len(role_codes),
        "menus": len(list(_iter_menu_tree(menus))),
        "permissions": len(permission_set),
        "role_permission_sets": len(role_menus),
    }
