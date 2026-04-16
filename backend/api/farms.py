"""
农场管理API
供农场端调用注册、心跳上报
供管理员查看农场状态
"""
from fastapi import APIRouter, HTTPException, Header, Request
from typing import List, Optional
from pydantic import BaseModel
from services.farm_manager import farm_manager
from logger import logger


router = APIRouter(prefix="/api/farms", tags=["farms"])


# ============ 请求模型 ============

class FarmRegisterRequest(BaseModel):
    """农场注册请求"""
    farm_id: str
    farm_name: str
    api_endpoint: str
    api_key: str
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None


class PrinterStatusData(BaseModel):
    """打印机状态数据"""
    id: str
    name: str
    model: Optional[str] = None
    status: str  # idle/printing/cooling/maintenance/error/offline
    current_order_id: Optional[str] = None
    nozzle_temp: Optional[int] = None
    bed_temp: Optional[int] = None
    print_progress: Optional[int] = 0
    max_nozzle_temp: Optional[int] = 300
    max_bed_temp: Optional[int] = 110
    build_volume: Optional[str] = None
    supported_materials: Optional[str] = None


class FarmHeartbeatRequest(BaseModel):
    """农场心跳请求"""
    farm_id: str
    printers: List[PrinterStatusData]


# ============ API端点 ============

@router.post("/register")
async def register_farm(
    request: FarmRegisterRequest,
    req: Request
):
    """
    农场注册
    农场端启动时调用此接口注册到主平台
    """
    try:
        db = req.app.state.db
        result = await farm_manager.register_farm(
            db=db,
            farm_id=request.farm_id,
            farm_name=request.farm_name,
            api_endpoint=request.api_endpoint,
            api_key=request.api_key,
            province=request.province,
            city=request.city,
            district=request.district
        )
        return result
    except Exception as e:
        logger.error(f"农场注册失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/heartbeat")
async def farm_heartbeat(
    request: FarmHeartbeatRequest,
    req: Request,
    x_api_key: Optional[str] = Header(None)
):
    """
    农场心跳
    农场端定时（30秒）调用此接口上报状态
    """
    try:
        # TODO: 验证API密钥
        
        db = req.app.state.db
        result = await farm_manager.update_farm_status(
            db=db,
            farm_id=request.farm_id,
            printers=[p.dict() for p in request.printers]
        )
        return result
    except Exception as e:
        logger.error(f"农场心跳失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_farms(
    req: Request,
    status: Optional[str] = None
):
    """
    查询农场列表
    管理员查看所有农场状态
    """
    try:
        db = req.app.state.db
        query = """
            SELECT farm_id, farm_name, status, total_printers, idle_printers,
                   busy_printers, offline_printers, province, city, district,
                   last_heartbeat, total_orders, completed_orders, enabled
            FROM farm_status
        """
        
        if status:
            query += " WHERE status = $1 ORDER BY priority DESC, farm_name"
            farms = await db.fetch(query, status)
        else:
            query += " ORDER BY priority DESC, farm_name"
            farms = await db.fetch(query)
        
        return {
            "farms": [
                {
                    "farm_id": f["farm_id"],
                    "farm_name": f["farm_name"],
                    "status": f["status"],
                    "total_printers": f["total_printers"],
                    "idle_printers": f["idle_printers"],
                    "busy_printers": f["busy_printers"],
                    "offline_printers": f["offline_printers"],
                    "province": f["province"],
                    "city": f["city"],
                    "district": f["district"],
                    "last_heartbeat": f["last_heartbeat"].isoformat() if f["last_heartbeat"] else None,
                    "total_orders": f["total_orders"],
                    "completed_orders": f["completed_orders"],
                    "enabled": f["enabled"]
                }
                for f in farms
            ]
        }
    except Exception as e:
        logger.error(f"查询农场列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{farm_id}/printers")
async def get_farm_printers(
    farm_id: str,
    req: Request
):
    """
    查询农场的打印机状态
    """
    try:
        db = req.app.state.db
        query = """
            SELECT printer_id, printer_name, printer_model, status,
                   current_order_id, nozzle_temp, bed_temp, print_progress,
                   build_volume, supported_materials, last_update
            FROM printer_status
            WHERE farm_id = $1
            ORDER BY printer_name
        """
        printers = await db.fetch(query, farm_id)
        
        return {
            "printers": [
                {
                    "printer_id": p["printer_id"],
                    "printer_name": p["printer_name"],
                    "printer_model": p["printer_model"],
                    "status": p["status"],
                    "current_order_id": p["current_order_id"],
                    "nozzle_temp": p["nozzle_temp"],
                    "bed_temp": p["bed_temp"],
                    "print_progress": p["print_progress"],
                    "build_volume": p["build_volume"],
                    "supported_materials": p["supported_materials"],
                    "last_update": p["last_update"].isoformat() if p["last_update"] else None
                }
                for p in printers
            ]
        }
    except Exception as e:
        logger.error(f"查询农场打印机失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_farm_stats(req: Request):
    """
    获取农场统计信息
    """
    try:
        db = req.app.state.db
        query = """
            SELECT 
                COUNT(*) as total_farms,
                SUM(CASE WHEN status = 'online' THEN 1 ELSE 0 END) as online_farms,
                SUM(total_printers) as total_printers,
                SUM(idle_printers) as idle_printers,
                SUM(busy_printers) as busy_printers
            FROM farm_status
            WHERE enabled = TRUE
        """
        stats = await db.fetchrow(query)
        
        return {
            "total_farms": stats["total_farms"] or 0,
            "online_farms": stats["online_farms"] or 0,
            "total_printers": stats["total_printers"] or 0,
            "idle_printers": stats["idle_printers"] or 0,
            "busy_printers": stats["busy_printers"] or 0
        }
    except Exception as e:
        logger.error(f"获取农场统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 农场拉取订单接口 ============

@router.get("/orders/pending")
async def get_pending_orders_for_farm(
    farm_id: str,
    req: Request,
    limit: int = 10,
    x_api_key: Optional[str] = Header(None)
):
    """
    农场拉取待处理的订单
    
    农场端可以主动调用此接口获取分配给自己但尚未接收的订单
    """
    try:
        db = req.app.state.db
        
        # 验证API密钥
        farm_query = """
            SELECT farm_id, api_key, status
            FROM farm_status
            WHERE farm_id = $1
        """
        farm = await db.fetchrow(farm_query, farm_id)
        
        if not farm:
            raise HTTPException(status_code=404, detail="农场不存在")
        
        if farm["status"] != "online":
            raise HTTPException(status_code=403, detail="农场未在线")
        
        # 简单的API密钥验证（生产环境应使用更安全的方式）
        if x_api_key and x_api_key != farm["api_key"]:
            raise HTTPException(status_code=401, detail="API密钥无效")
        
        # 查询分配给该农场但状态为assigned的订单
        orders_query = """
            SELECT 
                oa.order_id,
                oa.assigned_at,
                o.user_id,
                o.total_amount,
                po.asset_id,
                po.print_specs,
                po.estimated_weight,
                a.model_url,
                a.prompt,
                a.image_url
            FROM order_assignments oa
            JOIN orders o ON oa.order_id = o.id
            JOIN print_orders po ON o.id = po.order_id
            JOIN assets a ON po.asset_id = a.id
            WHERE oa.farm_id = $1
              AND oa.status = 'assigned'
            ORDER BY oa.assigned_at ASC
            LIMIT $2
        """
        
        orders = await db.fetch(orders_query, farm_id, min(limit, 50))
        
        # 转换为JSON格式
        import json
        order_list = []
        for order in orders:
            print_specs = order["print_specs"]
            if isinstance(print_specs, str):
                print_specs = json.loads(print_specs)
            
            order_list.append({
                "order_id": str(order["order_id"]),
                "user_id": str(order["user_id"]),
                "asset_id": str(order["asset_id"]),
                "model_url": order["model_url"],
                "prompt": order["prompt"],
                "image_url": order["image_url"],
                "print_specs": print_specs,
                "estimated_weight": float(order["estimated_weight"]),
                "total_amount": float(order["total_amount"]),
                "assigned_at": order["assigned_at"].isoformat() if order["assigned_at"] else None
            })
        
        logger.info(f"农场 {farm_id} 拉取了 {len(order_list)} 个待处理订单")
        
        return {
            "success": True,
            "count": len(order_list),
            "orders": order_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取待处理订单失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/{order_id}/accept")
async def accept_order(
    order_id: str,
    farm_id: str,
    req: Request,
    x_api_key: Optional[str] = Header(None)
):
    """
    农场确认接收订单
    
    农场端接收到订单后调用此接口确认
    """
    try:
        db = req.app.state.db
        
        # 验证农场
        farm_query = """
            SELECT farm_id, api_key
            FROM farm_status
            WHERE farm_id = $1
        """
        farm = await db.fetchrow(farm_query, farm_id)
        
        if not farm:
            raise HTTPException(status_code=404, detail="农场不存在")
        
        if x_api_key and x_api_key != farm["api_key"]:
            raise HTTPException(status_code=401, detail="API密钥无效")
        
        # 更新订单分配状态
        update_query = """
            UPDATE order_assignments
            SET status = 'accepted',
                accepted_at = CURRENT_TIMESTAMP
            WHERE order_id = $1
              AND farm_id = $2
              AND status = 'assigned'
        """
        
        result = await db.execute(update_query, order_id, farm_id)
        
        # asyncpg 的 execute 返回状态字符串，如 "UPDATE 1"
        if "0" in result:
            raise HTTPException(status_code=404, detail="订单不存在或已被接收")
        
        logger.info(f"农场 {farm_id} 确认接收订单 {order_id}")
        
        return {
            "success": True,
            "message": "订单接收成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"接收订单失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders/{order_id}/reject")
async def reject_order(
    order_id: str,
    farm_id: str,
    reason: str,
    req: Request,
    x_api_key: Optional[str] = Header(None)
):
    """
    农场拒绝订单
    
    农场端无法处理订单时调用此接口拒绝，系统会重新分配
    """
    try:
        db = req.app.state.db
        
        # 验证农场
        farm_query = """
            SELECT farm_id, api_key
            FROM farm_status
            WHERE farm_id = $1
        """
        farm = await db.fetchrow(farm_query, farm_id)
        
        if not farm:
            raise HTTPException(status_code=404, detail="农场不存在")
        
        if x_api_key and x_api_key != farm["api_key"]:
            raise HTTPException(status_code=401, detail="API密钥无效")
        
        # 更新订单分配状态
        update_query = """
            UPDATE order_assignments
            SET status = 'rejected',
                failure_reason = $3,
                retry_count = retry_count + 1
            WHERE order_id = $1
              AND farm_id = $2
              AND status IN ('assigned', 'accepted')
        """
        
        result = await db.execute(update_query, order_id, farm_id, reason)
        
        # asyncpg 的 execute 返回状态字符串，如 "UPDATE 1"
        if "0" in result:
            raise HTTPException(status_code=404, detail="订单不存在或状态不正确")
        
        logger.warning(f"农场 {farm_id} 拒绝订单 {order_id}，原因: {reason}")
        
        # TODO: 触发重新分配逻辑
        
        return {
            "success": True,
            "message": "订单已拒绝，系统将重新分配"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"拒绝订单失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
