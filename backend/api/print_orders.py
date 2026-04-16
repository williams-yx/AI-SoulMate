"""
打印订单相关的 API 路由
"""

import asyncio
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.dependencies import get_current_user
from config import Config
from logger import logger
from schemas.product import PrintOrderCreate
from services.print_slicer import PrintSliceError, slice_print_model

router = APIRouter(prefix="/api/print-orders", tags=["打印订单"])


def _normalize_print_material(material: Any) -> str:
    normalized = str(material or "PLA").strip().upper()
    if normalized in {"PLA_WHITE", "PLA"}:
        return normalized
    return normalized or "PLA"


def _get_material_density(material: Any) -> float:
    material_density = {
        "PLA": 1.24,
        "PLA_WHITE": 1.24,
        "ABS": 1.04,
        "PETG": 1.27,
        "TPU": 1.21,
        "NYLON": 1.14,
    }
    return material_density.get(_normalize_print_material(material), 1.24)


def _normalize_json_value(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return value


def _infer_model_format_from_url(url: Optional[str]) -> Optional[str]:
    normalized = str(url or "").strip().split("?", 1)[0]
    if "." not in normalized:
        return None
    return normalized.rsplit(".", 1)[-1].strip().lower() or None
def _update_order_items_payload(
    items: Any,
    *,
    estimated_weight: float,
    price_per_gram: float,
) -> tuple[list[dict[str, Any]], float]:
    payload = _normalize_json_value(items, [])
    if not isinstance(payload, list):
        payload = []

    updated_items: list[dict[str, Any]] = []
    total_amount = 0.0

    for raw_item in payload:
        item = raw_item if isinstance(raw_item, dict) else {}
        next_item = dict(item)
        if next_item.get("type") == "print":
            next_item["price"] = price_per_gram
            next_item["quantity"] = estimated_weight
        updated_items.append(next_item)

        try:
            total_amount += float(next_item.get("price", 0) or 0) * float(next_item.get("quantity", 0) or 0)
        except (TypeError, ValueError):
            continue

    return updated_items, round(total_amount, 2)


async def _resolve_print_source_model(
    db,
    *,
    asset_id: str,
    user_id: str,
    fallback_model_url: str,
) -> tuple[str, Optional[str]]:
    row = await db.fetchrow(
        """
        SELECT params
        FROM studio_history
        WHERE asset_id = $1
          AND user_id = $2
        ORDER BY created_at DESC
        LIMIT 1
        """,
        asset_id,
        user_id,
    )
    params = _normalize_json_value(row["params"], {}) if row else {}
    if isinstance(params, dict):
        gcode_source_model_url = str(params.get("gcode_source_model_url") or "").strip()
        gcode_source_model_format = str(params.get("gcode_source_model_format") or "").strip().lower() or None
        if gcode_source_model_url:
            return gcode_source_model_url, gcode_source_model_format
    return fallback_model_url, None


async def _run_print_job_slice(app, print_job_id: str) -> None:
    db = app.state.db
    try:
        await db.execute(
            """
            UPDATE orders
            SET status = 'pricing',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = (
                SELECT order_id
                FROM print_orders
                WHERE print_job_id = $1
            )
            """,
            print_job_id,
        )

        await db.execute(
            """
            UPDATE print_jobs
            SET status = 'slicing',
                slice_status = 'processing',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            print_job_id,
        )

        row = await db.fetchrow(
            """
            SELECT
                pj.id,
                pj.user_id,
                po.order_id,
                po.print_specs,
                po.price_per_gram,
                o.items AS order_items_payload
            FROM print_jobs pj
            JOIN print_orders po ON po.print_job_id = pj.id
            JOIN orders o ON o.id = po.order_id
            WHERE pj.id = $1
            """,
            print_job_id,
        )
        if not row:
            raise PrintSliceError("打印任务不存在")

        print_specs = _normalize_json_value(row["print_specs"], {})
        if not isinstance(print_specs, dict):
            print_specs = {}
        result = await slice_print_model(
            job_id=str(row["id"]),
            user_id=str(row["user_id"]),
            model_url=print_specs.get("model_url", ""),
            material=print_specs.get("material", "PLA"),
            height=print_specs.get("height", "default"),
        )

        updated_specs = {
            **print_specs,
            "slice_file_key": result["oss_key"],
            "slice_file_url": result["public_url"],
            "slice_file_name": result["file_name"],
            "slice_file_size": result["file_size"],
        }
        slicer_metadata = result.get("slicer_metadata") or {}
        if slicer_metadata:
            updated_specs["slicer_metadata"] = slicer_metadata
            if slicer_metadata.get("estimated_weight_grams") is not None:
                updated_specs["slicer_estimated_weight"] = slicer_metadata["estimated_weight_grams"]
                updated_specs["estimated_weight"] = slicer_metadata["estimated_weight_grams"]
            if slicer_metadata.get("estimated_print_time_seconds") is not None:
                updated_specs["slicer_estimated_print_time_seconds"] = slicer_metadata["estimated_print_time_seconds"]

        estimated_weight = slicer_metadata.get("estimated_weight_grams")
        price_per_gram = float(row["price_per_gram"] or 0)

        if estimated_weight is None:
            fallback_weight = print_specs.get("estimated_weight")
            if fallback_weight is None:
                raise PrintSliceError("切片完成但未解析到克重信息")
            estimated_weight = fallback_weight
            updated_specs["weight_source"] = "fallback_estimate"

        estimated_weight = float(estimated_weight)

        await db.execute(
            """
            UPDATE print_jobs
            SET status = 'awaiting_payment',
                slice_status = 'ready',
                slice_file_key = $2,
                slice_file_url = $3,
                slice_file_name = $4,
                last_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            print_job_id,
            result["oss_key"],
            result["public_url"],
            result["file_name"],
        )

        await db.execute(
            """
            UPDATE print_orders
            SET print_specs = $2::jsonb,
                estimated_weight = COALESCE($3, estimated_weight),
                updated_at = CURRENT_TIMESTAMP
            WHERE print_job_id = $1
            """,
            print_job_id,
            json.dumps(updated_specs),
            estimated_weight,
        )

        order_items_payload, total_amount = _update_order_items_payload(
            row["order_items_payload"],
            estimated_weight=estimated_weight,
            price_per_gram=price_per_gram,
        )
        print_item_total = round(estimated_weight * price_per_gram, 2)
        print_item_specs = {
            "height": print_specs.get("height"),
            "material": print_specs.get("material"),
            "estimated_weight": estimated_weight,
            "slicer_estimated_weight": estimated_weight,
        }

        await db.execute(
            """
            UPDATE order_items
            SET quantity = $2,
                unit_price = $3,
                total_price = $4,
                specs = $5::jsonb
            WHERE order_id = $1
              AND product_type = 'print'
            """,
            row["order_id"],
            max(1, int(round(estimated_weight))),
            price_per_gram,
            print_item_total,
            json.dumps(print_item_specs),
        )
        await db.execute(
            """
            UPDATE orders
            SET status = 'pending',
                items = $2::jsonb,
                total_amount = $3,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            row["order_id"],
            json.dumps(order_items_payload),
            total_amount,
        )

        logger.info("打印任务切片完成: print_job_id=%s", print_job_id)
    except Exception as exc:
        logger.exception("打印任务切片失败: print_job_id=%s", print_job_id)
        await db.execute(
            """
            UPDATE print_jobs
            SET status = 'failed',
                slice_status = 'failed',
                last_error = $2,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            print_job_id,
            str(exc),
        )
        await db.execute(
            """
            UPDATE orders
            SET status = 'pricing_failed',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = (
                SELECT order_id
                FROM print_orders
                WHERE print_job_id = $1
            )
            """,
            print_job_id,
        )


@router.post("/estimate-weight")
async def estimate_print_weight(
    estimate_data: Dict[str, Any],
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    估算打印克重和价格
    
    用于前端在用户选择打印参数时实时显示预估价格
    """
    try:
        height = estimate_data.get("height", "5cm")
        material = _normalize_print_material(estimate_data.get("material", "PLA_WHITE"))
        model_volume = estimate_data.get("model_volume")  # 如果前端能提供模型体积（cm³）

        density = _get_material_density(material)
        height_cm = float(height.replace('cm', ''))
        
        if model_volume:
            # 如果前端提供了模型体积，直接使用
            estimated_volume = float(model_volume)
        else:
            # 简化估算：假设模型是一个立方体，边长约为高度的70%
            estimated_volume = (height_cm * 0.7) ** 3
        
        # 计算克重
        estimated_weight = estimated_volume * density
        
        # 添加20%的支撑材料损耗
        estimated_weight = estimated_weight * 1.2
        
        # 四舍五入
        estimated_weight = round(estimated_weight, 1)
        
        # 获取单价
        app_state = request.app.state
        db = app_state.db
        
        print_product = await db.fetchrow(
            """
            SELECT p.specs
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE c.name = 'Print Service' 
              AND p.price_type = 'weight'
              AND p.status = 'active'
            LIMIT 1
            """
        )
        
        price_per_gram = 2.00
        if print_product and print_product["specs"]:
            try:
                specs = print_product["specs"]
                if isinstance(specs, str):
                    specs = json.loads(specs)
                if isinstance(specs, dict):
                    price_per_gram = float(specs.get("price_per_gram", 2.00))
            except Exception:
                pass
        
        total_price = estimated_weight * price_per_gram
        
        return {
            "estimated_weight": estimated_weight,
            "estimated_volume": round(estimated_volume, 2),
            "material": material,
            "density": density,
            "height": height,
            "price_per_gram": price_per_gram,
            "total_price": round(total_price, 2),
            "note": "此为预估价格，实际价格以打印完成后的实际克重为准"
        }
        
    except Exception as e:
        logger.error(f"估算打印克重失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"估算失败: {str(e)}"
        )


@router.post("")
async def create_print_order(
    print_data: PrintOrderCreate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """创建打印订单（从3D模型一键下单）"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    # 1. 验证asset是否存在且属于当前用户
    asset = await db.fetchrow(
        "SELECT id, author_id, model_url, prompt FROM assets WHERE id = $1",
        print_data.asset_id,
    )

    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="3D模型不存在")

    if asset["author_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="无权打印此模型"
        )

    source_model_url, source_model_format = await _resolve_print_source_model(
        db,
        asset_id=str(asset["id"]),
        user_id=str(current_user["id"]),
        fallback_model_url=asset["model_url"],
    )
    resolved_source_format = (source_model_format or _infer_model_format_from_url(source_model_url) or "").strip().lower()
    if resolved_source_format != "stl":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前仅支持 STL 格式模型打印，请先生成 STL 格式后再下单",
        )

    # 2. 获取打印服务商品（Print Service分类下的按克重计价商品）
    print_product = await db.fetchrow(
        """
        SELECT p.id, p.name, p.description, p.price, p.price_type, p.specs
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE c.name = 'Print Service' 
          AND p.price_type = 'weight'
          AND p.status = 'active'
        LIMIT 1
        """,
    )

    if not print_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="打印服务商品不存在"
        )

    # 3. 先入切片定价流程，金额在真实 G-code 克重解析完成后回写
    estimated_weight = print_data.estimated_weight

    if not estimated_weight:
        height_cm = float(print_data.height.replace('cm', ''))
        normalized_material = _normalize_print_material(print_data.material)
        density = _get_material_density(normalized_material)
        estimated_volume = (height_cm * 0.7) ** 3
        estimated_weight = round(estimated_volume * density * 1.2, 1)
        print_data.material = normalized_material
    else:
        print_data.material = _normalize_print_material(print_data.material)
    
    price_per_gram = 2.00  # 2元/g

    # 从商品specs中获取单价（如果有）
    try:
        specs = print_product["specs"]
        if isinstance(specs, str):
            specs = json.loads(specs)
        if isinstance(specs, dict):
            price_per_gram = float(specs.get("price_per_gram", 2.00))
    except Exception:
        pass

    logger.info(
        "打印订单进入切片定价流程: asset_id=%s, user_id=%s, material=%s, height=%s",
        print_data.asset_id,
        current_user["id"],
        print_data.material,
        print_data.height,
    )

    # 4. 使用事务创建订单、订单明细、打印任务、打印订单关联
    async with db.transaction() as conn:
        # 4.1 创建订单主记录
        order_row = await conn.fetchrow(
            """
            INSERT INTO orders (user_id, items, total_amount, payment_method, status)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            current_user["id"],
            json.dumps([{
                "id": str(print_product["id"]),
                "name": print_product["name"],
                "price": price_per_gram,
                "quantity": 0,
                "type": "print"
            }]),
            0,
            "demo",
            "pricing",
        )

        order_id = str(order_row["id"])

        # 4.2 创建打印任务
        target_client_id = (Config.PRINT_ALLOWED_CLIENT_ID or "").strip() or (Config.PRINT_DEFAULT_TARGET_CLIENT_ID or None)
        print_job_row = await conn.fetchrow(
            """
            INSERT INTO print_jobs (
                user_id, asset_id, prompt, status, slice_status, target_client_id, credits_used
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
            """,
            current_user["id"],
            print_data.asset_id,
            asset["prompt"],
            "queued",
            "queued",
            target_client_id,
            0,
        )

        print_job_id = str(print_job_row["id"])

        # 4.3 创建订单明细
        product_snapshot = {
            "id": str(print_product["id"]),
            "name": print_product["name"],
            "description": print_product["description"],
            "price": price_per_gram,
            "price_type": "weight",
            "material": print_data.material,
            "height": print_data.height,
        }

        await conn.execute(
            """
            INSERT INTO order_items (
                order_id, product_id, product_type, product_snapshot,
                quantity, unit_price, total_price, specs
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            order_id,
            print_product["id"],
            "print",
            json.dumps(product_snapshot),
            max(1, int(round(float(estimated_weight)))) if estimated_weight else 1,
            price_per_gram,
            0,
            json.dumps({
                "height": print_data.height,
                "material": print_data.material,
                "estimated_weight": estimated_weight,
            }),
        )

        # 4.4 创建打印订单关联
        await conn.execute(
            """
            INSERT INTO print_orders (
                order_id, print_job_id, asset_id, print_specs,
                estimated_weight, price_per_gram
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            order_id,
            print_job_id,
            print_data.asset_id,
            json.dumps({
                "height": print_data.height,
                "material": print_data.material,
                "model_url": source_model_url,
                "source_model_format": source_model_format,
                "original_model_url": asset["model_url"],
                "prompt": asset["prompt"],
            }),
            estimated_weight,
            price_per_gram,
        )

        logger.info(
            f"打印订单创建成功: order_id={order_id}, print_job_id={print_job_id}, "
            f"asset_id={print_data.asset_id}, user_id={current_user['id']}"
        )

    asyncio.create_task(_run_print_job_slice(request.app, print_job_id))

    return {
        "order_id": order_id,
        "print_job_id": print_job_id,
        "total_amount": 0,
        "estimated_weight": estimated_weight,
        "price_per_gram": price_per_gram,
        "task_status": "pricing",
        "message": "打印订单已创建，正在切片并核算真实克重，完成后将进入待支付"
    }


@router.get("/{order_id}/print-job")
async def get_print_job_by_order(
    order_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """根据订单ID获取打印任务信息"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    # 验证订单归属
    order = await db.fetchrow(
        "SELECT id FROM orders WHERE id = $1 AND user_id = $2",
        order_id,
        current_user["id"],
    )

    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="订单不存在")

    # 获取打印订单信息（含切片状态、打印农场分配信息、时间戳）
    print_order = await db.fetchrow(
        """
        SELECT 
            po.id, po.order_id, po.print_job_id, po.asset_id,
            po.print_specs, po.estimated_weight, po.actual_weight,
            po.price_per_gram, po.shipping_company, po.tracking_number,
            po.shipped_at, po.received_at, po.created_at, po.updated_at,
            pj.status as print_status,
            pj.slice_status,
            pj.slice_file_key,
            pj.slice_file_name,
            pj.claimed_by_client_id,
            pj.target_client_id,
            pj.claimed_at,
            pj.started_at,
            pj.completed_at,
            a.model_url, a.prompt, a.image_url
        FROM print_orders po
        JOIN print_jobs pj ON po.print_job_id = pj.id
        JOIN assets a ON po.asset_id = a.id
        WHERE po.order_id = $1
        """,
        order_id,
    )

    if not print_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="打印订单不存在"
        )

    # 转换OSS URL为签名URL
    result = dict(print_order)
    from utils.oss_util import oss_manager
    
    if result.get("image_url") and result["image_url"].startswith("oss://"):
        signed_url = oss_manager.generate_presigned_url(
            result["image_url"][len("oss://"):], expires=3600
        )
        if signed_url:
            result["image_url"] = signed_url
            
    if result.get("model_url") and result["model_url"].startswith("oss://"):
        signed_url = oss_manager.generate_presigned_url(
            result["model_url"][len("oss://"):], expires=3600
        )
        if signed_url:
            result["model_url"] = signed_url

    # 查询打印农场分配信息
    farm_assignment = await db.fetchrow(
        """
        SELECT 
            oa.farm_id, oa.printer_id, oa.status as assignment_status,
            oa.assigned_at, oa.accepted_at, oa.completed_at as assignment_completed_at,
            fs.farm_name, fs.province, fs.city
        FROM order_assignments oa
        LEFT JOIN farm_status fs ON fs.farm_id = oa.farm_id
        WHERE oa.order_id = $1
        """,
        order_id,
    )
    if farm_assignment:
        result["farm_assignment"] = {
            "farm_id": str(farm_assignment["farm_id"]) if farm_assignment["farm_id"] else None,
            "farm_name": farm_assignment["farm_name"],
            "province": farm_assignment["province"],
            "city": farm_assignment["city"],
            "printer_id": str(farm_assignment["printer_id"]) if farm_assignment["printer_id"] else None,
            "assignment_status": farm_assignment["assignment_status"],
            "assigned_at": farm_assignment["assigned_at"].isoformat() if farm_assignment["assigned_at"] else None,
            "accepted_at": farm_assignment["accepted_at"].isoformat() if farm_assignment["accepted_at"] else None,
        }
    else:
        result["farm_assignment"] = None

    # 序列化时间戳字段
    for ts_field in ("claimed_at", "started_at", "completed_at", "shipped_at", "received_at"):
        val = result.get(ts_field)
        if val is not None:
            try:
                result[ts_field] = val.isoformat()
            except Exception:
                result[ts_field] = str(val)

    return result


__all__ = ["router"]
