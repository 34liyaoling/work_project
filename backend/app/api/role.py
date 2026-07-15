"""岗位管理 API

提供新岗位发现、审核、既有岗位更新、岗位详情查询等接口。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.schemas import (
    AuditQueueItem,
    CommonResponse,
    JobRoleResponse,
    PageResponse,
    Pagination,
    RoleDiscoverRequest,
    RoleReviewRequest,
)
from app.core.database import get_db
from app.core.logger import log
from app.models.job_role import AuditLog, JobRoleCard

router = APIRouter()


def _to_role_response(record: JobRoleCard) -> JobRoleResponse:
    """将 ORM 对象转换为响应模型"""
    return JobRoleResponse(
        role_id=record.role_id,
        name=record.name or "",
        category=record.category,
        level=record.level,
        core_responsibilities=record.core_responsibilities or [],
        required_skills=record.required_skills or [],
        preferred_skills=record.preferred_skills or [],
        typical_scenarios=record.typical_scenarios or [],
        confidence=record.confidence or 0.0,
        evidence_sources=record.evidence_sources or [],
        is_new=record.is_new or 0,
        is_reviewed=record.is_reviewed or 0,
        reviewed_by=record.reviewed_by,
        reviewed_at=record.reviewed_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get("/new", response_model=CommonResponse, summary="新岗位发现列表")
def list_new_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
):
    """获取系统自动发现的新岗位定义列表（is_new=1）

    - 支持按类别、最低置信度过滤
    - 默认按置信度倒序排序
    """
    q = db.query(JobRoleCard).filter(JobRoleCard.is_new == 1)
    if category:
        q = q.filter(JobRoleCard.category == category)
    if min_confidence > 0:
        q = q.filter(JobRoleCard.confidence >= min_confidence)

    total = q.count()
    items = q.order_by(desc(JobRoleCard.confidence)).offset((page - 1) * page_size).limit(page_size).all()
    data = [_to_role_response(r).model_dump() for r in items]
    return CommonResponse(data=PageResponse(
        items=data,
        pagination=Pagination(page=page, page_size=page_size, total=total),
    ).model_dump())


@router.get("/updates", response_model=CommonResponse, summary="既有岗位更新列表")
def list_role_updates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """获取近期发生更新的既有岗位（updated_at 在 days 天内）

    - 反映岗位定义的动态演化
    - 默认按更新时间倒序
    """
    cutoff = datetime.now() - timedelta(days=days)
    q = db.query(JobRoleCard).filter(
        JobRoleCard.is_new == 0,
        JobRoleCard.updated_at >= cutoff,
    )
    total = q.count()
    items = q.order_by(desc(JobRoleCard.updated_at)).offset((page - 1) * page_size).limit(page_size).all()
    data = [_to_role_response(r).model_dump() for r in items]
    return CommonResponse(data=PageResponse(
        items=data,
        pagination=Pagination(page=page, page_size=page_size, total=total),
    ).model_dump())


@router.get("/{role_id}", response_model=CommonResponse, summary="获取岗位详情")
def get_role_detail(role_id: str, db: Session = Depends(get_db)):
    """根据 role_id 获取岗位定义详情"""
    record = db.query(JobRoleCard).filter(JobRoleCard.role_id == role_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"岗位 {role_id} 不存在")
    return CommonResponse(data=_to_role_response(record).model_dump())


@router.get("/", response_model=CommonResponse, summary="岗位列表")
def list_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    level: Optional[str] = None,
    is_reviewed: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """分页查询岗位列表"""
    q = db.query(JobRoleCard)
    if category:
        q = q.filter(JobRoleCard.category == category)
    if level:
        q = q.filter(JobRoleCard.level == level)
    if is_reviewed is not None:
        q = q.filter(JobRoleCard.is_reviewed == is_reviewed)
    total = q.count()
    items = q.order_by(desc(JobRoleCard.confidence)).offset((page - 1) * page_size).limit(page_size).all()
    data = [_to_role_response(r).model_dump() for r in items]
    return CommonResponse(data=PageResponse(
        items=data,
        pagination=Pagination(page=page, page_size=page_size, total=total),
    ).model_dump())


@router.post("/{role_id}/review", response_model=CommonResponse, summary="审核岗位")
def review_role(role_id: str, payload: RoleReviewRequest, db: Session = Depends(get_db)):
    """对岗位进行人工审核：approve / reject / modify

    - approve: 标记 is_reviewed=1，写入审核人
    - reject: 从数据库删除记录
    - modify: 更新岗位字段并标记为已审核
    - 同步写入审计日志
    """
    if payload.action not in {"approve", "reject", "modify"}:
        raise HTTPException(status_code=400, detail=f"不支持的审核动作: {payload.action}")

    record = db.query(JobRoleCard).filter(JobRoleCard.role_id == role_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"岗位 {role_id} 不存在")

    try:
        if payload.action == "reject":
            # 写审计
            audit = AuditLog(
                entity_type="jobrole",
                entity_id=role_id,
                entity_data={"name": record.name, "category": record.category},
                reason="人工拒绝",
                status="rejected",
                reviewed_by=payload.reviewer or "anonymous",
                reviewed_at=datetime.now(),
                review_comment=payload.comment,
            )
            db.add(audit)
            db.delete(record)
        else:
            if payload.action == "modify" and payload.modified_data:
                # 仅更新允许的字段
                for field in ("name", "category", "level"):
                    if field in payload.modified_data:
                        setattr(record, field, payload.modified_data[field])
                if "core_responsibilities" in payload.modified_data:
                    record.core_responsibilities = payload.modified_data["core_responsibilities"]
                if "required_skills" in payload.modified_data:
                    record.required_skills = payload.modified_data["required_skills"]
                if "preferred_skills" in payload.modified_data:
                    record.preferred_skills = payload.modified_data["preferred_skills"]
            record.is_reviewed = 1
            record.reviewed_by = payload.reviewer or "anonymous"
            record.reviewed_at = datetime.now()
            record.is_new = 0  # 审核后转为既有岗位

            audit = AuditLog(
                entity_type="jobrole",
                entity_id=role_id,
                entity_data={"name": record.name, "category": record.category},
                reason="人工通过" if payload.action == "approve" else "人工修改",
                status="approved",
                reviewed_by=record.reviewed_by,
                reviewed_at=record.reviewed_at,
                review_comment=payload.comment,
            )
            db.add(audit)

        db.commit()
    except Exception as e:
        db.rollback()
        log.error(f"岗位审核失败: {e}")
        raise HTTPException(status_code=500, detail=f"审核失败: {str(e)}")

    return CommonResponse(data={
        "role_id": role_id,
        "action": payload.action,
        "is_reviewed": 1 if payload.action != "reject" else 0,
    })


@router.get("/audit/queue", response_model=CommonResponse, summary="审核队列")
def get_audit_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="pending/approved/rejected"),
    db: Session = Depends(get_db),
):
    """获取待审核实体队列

    - 包含尚未审核或最近审核的实体
    - 供审核界面展示
    """
    q = db.query(AuditLog)
    if status:
        q = q.filter(AuditLog.status == status)
    total = q.count()
    items = q.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    data = [
        AuditQueueItem(
            id=r.id,
            entity_type=r.entity_type or "jobrole",
            entity_id=r.entity_id or "",
            entity_data=r.entity_data or {},
            reason=r.reason,
            status=r.status or "pending",
            reviewed_by=r.reviewed_by,
            reviewed_at=r.reviewed_at,
            review_comment=r.review_comment,
            created_at=r.created_at or datetime.now(),
        ).model_dump()
        for r in items
    ]
    return CommonResponse(data=PageResponse(
        items=data,
        pagination=Pagination(page=page, page_size=page_size, total=total),
    ).model_dump())


@router.post("/discover", response_model=CommonResponse, summary="触发岗位发现")
def trigger_discovery(payload: RoleDiscoverRequest, db: Session = Depends(get_db)):
    """触发一次岗位发现流程（模拟）

    - 实际生产环境会调用 LLM/聚类服务从最新 JD 中提取新岗位
    - 这里返回任务 ID，前端可轮询
    """
    task_id = f"discover_{uuid.uuid4().hex[:12]}"
    # 简化处理：返回参数化响应
    return CommonResponse(data={
        "task_id": task_id,
        "status": "queued",
        "days": payload.days,
        "min_source_count": payload.min_source_count,
        "started_at": datetime.now().isoformat(),
        "message": "岗位发现任务已入队，预计 30s 内完成",
    })
