"""
项目相关的 API 路由
"""

from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Request, status

from schemas import Project
from api.dependencies import get_current_user
from services.ai_service import AIService
from logger import logger


router = APIRouter(prefix="/api/projects", tags=["项目"])


@router.post("")
async def create_project(
    project: Project,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """创建新项目"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    row = await db.fetchrow(
        """
        INSERT INTO projects (user_id, title, description, prompt, style_model)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        current_user["id"],
        project.title,
        project.description,
        project.prompt,
        project.style_model,
    )

    return {"project_id": str(row["id"])}


@router.post("/{project_id}/generate")
async def generate_model(
    project_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """生成 3D 模型"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    # 获取项目信息
    project = await db.fetchrow(
        "SELECT * FROM projects WHERE id = $1 AND user_id = $2",
        project_id,
        current_user["id"],
    )

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # 检查积分
    if current_user.get("credits", 0) < 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="积分不足")

    # 更新项目状态为 generating
    await db.execute(
        "UPDATE projects SET status = 'generating' WHERE id = $1",
        project_id,
    )

    try:
        # 调用 AI 服务生成模型
        result = await AIService.generate_3d_model(
            project["prompt"],
            project["style_model"],
        )

        # 扣除积分（先扣免费，再扣兑换，最后扣付费）
        from core.points import deduct_points
        ok = await deduct_points(
            db, 
            str(current_user["id"]), 
            result["credits_used"],
            reason="generate_3d",
            related_id=project_id
        )
        if not ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="积分不足")

        # 更新项目
        await db.execute(
            """
            UPDATE projects
            SET status = 'completed',
                model_url = $1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $2
            """,
            result["model_url"],
            project_id,
        )

        return {
            "status": "success",
            "model_url": result["model_url"],
            "credits_used": result["credits_used"],
        }

    except Exception as e:  # noqa: BLE001
        logger.error(f"生成 3D 模型失败: {e}")
        await db.execute(
            "UPDATE projects SET status = 'failed' WHERE id = $1",
            project_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Model generation failed",
        )


@router.get("")
async def get_projects(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取当前用户的项目列表"""
    app_state = request.app.state
    if not hasattr(app_state, "db_connected") or not app_state.db_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="数据库未连接"
        )

    db = app_state.db

    projects = await db.fetch(
        """
        SELECT id, title, description, status, model_url, created_at, updated_at
        FROM projects
        WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        current_user["id"],
    )

    return [dict(project) for project in projects]


__all__ = ["router"]
