"""
地址管理相关的 API 路由
"""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request, status

from schemas import Address
from api.dependencies import get_current_user
from logger import logger


router = APIRouter(prefix="/api/address", tags=["地址"])


@router.get("")
async def get_addresses(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取用户地址列表"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    addresses = await db.fetch(
        "SELECT * FROM addresses WHERE user_id = $1 ORDER BY is_default DESC, created_at DESC",
        current_user["id"],
    )

    return [dict(addr) for addr in addresses]


@router.post("")
async def create_address(
    address_data: Address,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """创建地址"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    # 如果设置为默认地址，取消其他默认地址
    if address_data.is_default:
        await db.execute(
            "UPDATE addresses SET is_default = FALSE WHERE user_id = $1",
            current_user["id"],
        )

    row = await db.fetchrow(
        """
        INSERT INTO addresses (user_id, name, phone, province, city, district, address, is_default)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """,
        current_user["id"],
        address_data.name,
        address_data.phone,
        address_data.province,
        address_data.city,
        address_data.district,
        address_data.address,
        address_data.is_default,
    )

    return {"address_id": str(row["id"])}


@router.put("/{address_id}")
async def update_address(
    address_id: str,
    address_data: Address,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新地址"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    if address_data.is_default:
        await db.execute(
            "UPDATE addresses SET is_default = FALSE WHERE user_id = $1 AND id != $2",
            current_user["id"],
            address_id,
        )

    result = await db.execute(
        """
        UPDATE addresses
        SET name = $1, phone = $2, province = $3, city = $4, district = $5,
            address = $6, is_default = $7
        WHERE id = $8 AND user_id = $9
        """,
        address_data.name,
        address_data.phone,
        address_data.province,
        address_data.city,
        address_data.district,
        address_data.address,
        address_data.is_default,
        address_id,
        current_user["id"],
    )

    if "0" in str(result):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    return {"message": "Address updated successfully"}


@router.delete("/{address_id}")
async def delete_address(
    address_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除地址"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    result = await db.execute(
        "DELETE FROM addresses WHERE id = $1 AND user_id = $2",
        address_id,
        current_user["id"],
    )

    if "0" in str(result):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    return {"message": "Address deleted successfully"}


__all__ = ["router"]
