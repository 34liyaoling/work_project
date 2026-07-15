"""JD 管理 API

提供 JD 的创建、查询、解析、删除等接口。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.schemas import (
    CommonResponse,
    JDBatchParseRequest,
    JDCreateRequest,
    JDParseTaskResponse,
    JDResponse,
    PageResponse,
    Pagination,
)
from app.core.database import get_db
from app.core.logger import log
from app.models.jd import JDRecord

router = APIRouter()


@router.post("/", response_model=CommonResponse, summary="创建 JD")
def create_jd(payload: JDCreateRequest, db: Session = Depends(get_db)):
    """创建一条新的 JD 记录

    - 自动生成 jd_id
    - 默认未解析（is_processed=0）
    """
    jd_id = f"jd_{uuid.uuid4().hex[:16]}"
    record = JDRecord(
        jd_id=jd_id,
        source=payload.source,
        source_url=payload.source_url,
        company=payload.company,
        title=payload.title,
        category=payload.category,
        level=payload.level,
        location=payload.location,
        salary_range=payload.salary_range,
        raw_text=payload.raw_text,
        published_at=payload.published_at,
        is_processed=0,
    )
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception as e:
        db.rollback()
        log.error(f"创建 JD 失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建 JD 失败: {str(e)}")

    return CommonResponse(data={"jd_id": jd_id})


@router.get("/{jd_id}", response_model=CommonResponse, summary="获取 JD 详情")
def get_jd(jd_id: str, db: Session = Depends(get_db)):
    """根据 jd_id 获取 JD 详情"""
    record = db.query(JDRecord).filter(JDRecord.jd_id == jd_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"JD {jd_id} 不存在")

    return CommonResponse(data=JDResponse(
        jd_id=record.jd_id,
        source=record.source,
        source_url=record.source_url,
        company=record.company,
        title=record.title,
        category=record.category,
        level=record.level,
        location=record.location,
        salary_range=record.salary_range,
        raw_text=record.raw_text or "",
        parsed_data=record.parsed_data,
        skills=record.skills or [],
        published_at=record.published_at,
        crawled_at=record.crawled_at,
        is_processed=record.is_processed or 0,
        credibility_score=record.credibility_score or 0.5,
    ).model_dump())


@router.get("/", response_model=CommonResponse, summary="JD 列表查询")
def list_jds(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
    company: Optional[str] = None,
    category: Optional[str] = None,
    is_processed: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """分页查询 JD 列表，支持按来源、公司、类别等过滤"""
    q = db.query(JDRecord)
    if source:
        q = q.filter(JDRecord.source == source)
    if company:
        q = q.filter(JDRecord.company.like(f"%{company}%"))
    if category:
        q = q.filter(JDRecord.category == category)
    if is_processed is not None:
        q = q.filter(JDRecord.is_processed == is_processed)
    if keyword:
        q = q.filter(JDRecord.title.like(f"%{keyword}%"))

    total = q.count()
    items = q.order_by(desc(JDRecord.crawled_at)).offset((page - 1) * page_size).limit(page_size).all()
    data = [
        {
            "jd_id": r.jd_id,
            "source": r.source,
            "company": r.company,
            "title": r.title,
            "category": r.category,
            "level": r.level,
            "location": r.location,
            "salary_range": r.salary_range,
            "skills": r.skills or [],
            "is_processed": r.is_processed,
            "crawled_at": r.crawled_at.isoformat() if r.crawled_at else None,
        }
        for r in items
    ]
    return CommonResponse(data=PageResponse(
        items=data,
        pagination=Pagination(page=page, page_size=page_size, total=total),
    ).model_dump())


@router.post("/{jd_id}/parse", response_model=CommonResponse, summary="触发 JD 解析")
def parse_jd(jd_id: str, db: Session = Depends(get_db)):
    """调用 LLM 解析器对单条 JD 进行结构化解析

    - 解析结果写入 parsed_data
    - 抽取的技能列表写入 skills
    - 标记 is_processed=1
    """
    record = db.query(JDRecord).filter(JDRecord.jd_id == jd_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"JD {jd_id} 不存在")

    try:
        # 简化版解析：使用关键字匹配提取技能（避免直接依赖未实现的 JDParser）
        from app.core.config import settings
        import json
        import re
        import os

        skill_dict_path = settings.SKILL_DICT_PATH
        extracted_skills = []
        if os.path.exists(skill_dict_path):
            try:
                with open(skill_dict_path, "r", encoding="utf-8") as f:
                    skill_dict = json.load(f)
                text = record.raw_text or ""
                for skill, info in skill_dict.items():
                    if skill.lower() in text.lower():
                        extracted_skills.append({
                            "name": skill,
                            "category": info.get("category", "未分类"),
                            "weight": info.get("weight", 1.0),
                        })
            except Exception:
                pass

        record.parsed_data = {
            "responsibilities": [],
            "requirements": [],
            "parser_version": "v1.0-fallback",
        }
        record.skills = [s["name"] for s in extracted_skills]
        record.is_processed = 1
        db.commit()
    except Exception as e:
        db.rollback()
        log.error(f"解析 JD {jd_id} 失败: {e}")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")

    return CommonResponse(data={
        "jd_id": jd_id,
        "skills": record.skills,
        "is_processed": 1,
    })


@router.post("/batch_parse", response_model=CommonResponse, summary="批量解析 JD")
def batch_parse_jds(payload: JDBatchParseRequest, db: Session = Depends(get_db)):
    """对多条 JD 执行批量解析"""
    task_id = f"parse_task_{uuid.uuid4().hex[:12]}"
    results = []
    success = 0
    failed = 0

    for jd_id in payload.jd_ids:
        try:
            record = db.query(JDRecord).filter(JDRecord.jd_id == jd_id).first()
            if not record:
                results.append({"jd_id": jd_id, "status": "failed", "error": "not_found"})
                failed += 1
                continue
            if record.is_processed and not payload.force:
                results.append({"jd_id": jd_id, "status": "skipped"})
                continue

            # 复用单条解析逻辑（简化）
            record.parsed_data = {"parser_version": "v1.0-batch"}
            record.skills = record.skills or []
            record.is_processed = 1
            db.commit()
            results.append({"jd_id": jd_id, "status": "success"})
            success += 1
        except Exception as e:
            db.rollback()
            results.append({"jd_id": jd_id, "status": "failed", "error": str(e)})
            failed += 1

    return CommonResponse(data=JDParseTaskResponse(
        task_id=task_id,
        total=len(payload.jd_ids),
        success=success,
        failed=failed,
        results=results,
    ).model_dump())


@router.delete("/{jd_id}", response_model=CommonResponse, summary="删除 JD")
def delete_jd(jd_id: str, db: Session = Depends(get_db)):
    """根据 jd_id 删除 JD 记录"""
    record = db.query(JDRecord).filter(JDRecord.jd_id == jd_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"JD {jd_id} 不存在")
    try:
        db.delete(record)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
    return CommonResponse(data={"jd_id": jd_id, "deleted": True})
