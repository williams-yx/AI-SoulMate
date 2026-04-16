"""
农场管理服务
负责农场状态管理、心跳检测、订单分配
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from logger import logger
import httpx


class FarmManager:
    """农场管理器"""
    
    def __init__(self):
        self.heartbeat_timeout_multiplier = 3  # 心跳超时倍数
    
    async def register_farm(
        self,
        db,  # DatabaseManager instance
        farm_id: str,
        farm_name: str,
        api_endpoint: str,
        api_key: str,
        province: str = None,
        city: str = None,
        district: str = None
    ) -> Dict[str, Any]:
        """
        注册农场
        
        Args:
            db: 数据库管理器
            farm_id: 农场ID（对应client端merchant_id）
            farm_name: 农场名称
            api_endpoint: 农场API地址
            api_key: API密钥
            province: 省份
            city: 城市
            district: 区县
        
        Returns:
            注册结果
        """
        try:
            # 检查是否已存在
            query = "SELECT id FROM farm_status WHERE farm_id = $1"
            existing = await db.fetchrow(query, farm_id)
            
            if existing:
                # 更新信息
                update_query = """
                    UPDATE farm_status 
                    SET farm_name = $2,
                        api_endpoint = $3,
                        api_key = $4,
                        province = $5,
                        city = $6,
                        district = $7,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE farm_id = $1
                """
                await db.execute(update_query, farm_id, farm_name, api_endpoint, 
                               api_key, province, city, district)
            else:
                # 新增农场
                insert_query = """
                    INSERT INTO farm_status (
                        farm_id, farm_name, api_endpoint, api_key,
                        province, city, district, status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'offline')
                """
                await db.execute(insert_query, farm_id, farm_name, api_endpoint,
                               api_key, province, city, district)
            
            logger.info(f"农场注册成功: {farm_name} ({farm_id})")
            
            return {
                "success": True,
                "farm_id": farm_id,
                "message": "农场注册成功"
            }
        
        except Exception as e:
            logger.error(f"农场注册失败: {str(e)}")
            raise
    
    async def update_farm_status(
        self,
        db,  # DatabaseManager instance
        farm_id: str,
        printers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        更新农场状态（心跳）
        
        Args:
            db: 数据库管理器
            farm_id: 农场ID
            printers: 打印机状态列表
        
        Returns:
            更新结果
        """
        try:
            # 统计打印机状态
            total_printers = len(printers)
            idle_printers = sum(1 for p in printers if p.get('status') == 'idle')
            busy_printers = sum(1 for p in printers if p.get('status') in ['printing', 'cooling'])
            offline_printers = sum(1 for p in printers if p.get('status') == 'offline')
            
            # 判断农场状态
            if offline_printers == total_printers:
                farm_status = 'offline'
            elif idle_printers == 0 and busy_printers > 0:
                farm_status = 'busy'
            else:
                farm_status = 'online'
            
            # 更新农场状态（移除payment_config字段）
            update_farm_query = """
                UPDATE farm_status 
                SET status = $2,
                    total_printers = $3,
                    idle_printers = $4,
                    busy_printers = $5,
                    offline_printers = $6,
                    last_heartbeat = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE farm_id = $1
            """
            await db.execute(update_farm_query, farm_id, farm_status, total_printers,
                           idle_printers, busy_printers, offline_printers)
            
            # 更新打印机状态
            for printer in printers:
                upsert_printer_query = """
                    INSERT INTO printer_status (
                        farm_id, printer_id, printer_name, printer_model,
                        status, current_order_id, nozzle_temp, bed_temp,
                        print_progress, max_nozzle_temp, max_bed_temp,
                        build_volume, supported_materials, last_update
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (farm_id, printer_id) DO UPDATE SET
                        printer_name = EXCLUDED.printer_name,
                        printer_model = EXCLUDED.printer_model,
                        status = EXCLUDED.status,
                        current_order_id = EXCLUDED.current_order_id,
                        nozzle_temp = EXCLUDED.nozzle_temp,
                        bed_temp = EXCLUDED.bed_temp,
                        print_progress = EXCLUDED.print_progress,
                        last_update = CURRENT_TIMESTAMP
                """
                await db.execute(upsert_printer_query,
                               farm_id,
                               printer.get('id'),
                               printer.get('name'),
                               printer.get('model'),
                               printer.get('status', 'offline'),
                               printer.get('current_order_id'),
                               printer.get('nozzle_temp'),
                               printer.get('bed_temp'),
                               printer.get('print_progress', 0),
                               printer.get('max_nozzle_temp', 300),
                               printer.get('max_bed_temp', 110),
                               printer.get('build_volume'),
                               printer.get('supported_materials'))
            
            return {
                "success": True,
                "farm_status": farm_status,
                "idle_printers": idle_printers
            }
        
        except Exception as e:
            logger.error(f"更新农场状态失败: {str(e)}")
            raise
    
    async def get_available_farm(
        self,
        db,  # DatabaseManager instance
        material: str = None,
        province: str = None,
        city: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取可用农场（用于订单分配）
        
        Args:
            db: 数据库管理器
            material: 所需材质
            province: 优先省份
            city: 优先城市
        
        Returns:
            农场信息，如果没有可用农场返回None
        """
        try:
            # 查询在线且有空闲打印机的农场
            query = """
                SELECT farm_id, farm_name, api_endpoint, idle_printers, priority, weight,
                       province, city
                FROM farm_status
                WHERE status = 'online'
                  AND enabled = TRUE
                  AND idle_printers > 0
                  AND last_heartbeat > $1
                ORDER BY 
                    CASE WHEN province = $2 AND city = $3 THEN 1
                         WHEN province = $2 THEN 2
                         ELSE 3 END,
                    priority DESC,
                    idle_printers DESC,
                    weight DESC
                LIMIT 1
            """
            
            timeout = datetime.utcnow() - timedelta(seconds=90)  # 90秒内有心跳
            
            farm = await db.fetchrow(query, timeout, province or '', city or '')
            
            if farm:
                return {
                    "farm_id": farm["farm_id"],
                    "farm_name": farm["farm_name"],
                    "api_endpoint": farm["api_endpoint"],
                    "idle_printers": farm["idle_printers"]
                }
            
            return None
        
        except Exception as e:
            logger.error(f"获取可用农场失败: {str(e)}")
            return None
    
    async def assign_order_to_farm(
        self,
        db,  # DatabaseManager instance
        order_id: str,
        farm_id: str
    ) -> Dict[str, Any]:
        """
        分配订单到农场
        
        Args:
            db: 数据库管理器
            order_id: 订单ID
            farm_id: 农场ID
        
        Returns:
            分配结果
        """
        try:
            # 记录分配
            insert_query = """
                INSERT INTO order_assignments (order_id, farm_id, status)
                VALUES ($1, $2, 'assigned')
            """
            await db.execute(insert_query, order_id, farm_id)
            
            # 更新订单状态
            update_order_query = """
                UPDATE print_orders
                SET status = 'assigned',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
            """
            await db.execute(update_order_query, order_id)
            
            logger.info(f"订单 {order_id} 已分配到农场 {farm_id}")
            
            return {
                "success": True,
                "order_id": order_id,
                "farm_id": farm_id
            }
        
        except Exception as e:
            logger.error(f"订单分配失败: {str(e)}")
            raise
    
    async def check_offline_farms(self, db):
        """检查离线农场（定时任务）"""
        try:
            timeout = datetime.utcnow() - timedelta(seconds=90)
            
            update_query = """
                UPDATE farm_status
                SET status = 'offline'
                WHERE last_heartbeat < $1
                  AND status != 'offline'
            """
            result = await db.execute(update_query, timeout)
            
            # asyncpg 返回 "UPDATE N" 格式的字符串
            if result and "UPDATE" in result:
                count = int(result.split()[-1])
                if count > 0:
                    logger.warning(f"检测到 {count} 个农场离线")
        
        except Exception as e:
            logger.error(f"检查离线农场失败: {str(e)}")


# 全局实例
farm_manager = FarmManager()
