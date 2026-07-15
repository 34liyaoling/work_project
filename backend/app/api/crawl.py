"""数据采集 API

负责启动采集任务、查询状态、生成模拟数据等。
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.schemas import (
    CommonResponse,
    CrawlLogItem,
    CrawlStartRequest,
    CrawlTaskResponse,
    MockDataRequest,
    PageResponse,
    Pagination,
)
from app.core.database import get_db
from app.core.logger import log
from app.models.jd import DataCrawlLog, JDRecord
from app.models.job_role import JobRoleCard

router = APIRouter()

# 简单的内存任务表（生产环境建议使用 Celery/Redis）
TASK_STORE: dict = {}


@router.post("/start", response_model=CommonResponse, summary="启动采集任务")
def start_crawl(payload: CrawlStartRequest, db: Session = Depends(get_db)):
    """启动指定来源的爬虫任务

    - 写入 DataCrawlLog
    - 模拟任务状态推进
    - 实际生产中可对接 Celery 异步执行
    """
    task_id = f"crawl_{uuid.uuid4().hex[:12]}"
    log_entry = DataCrawlLog(
        source=payload.source,
        task_type=payload.task_type,
        started_at=datetime.now(),
        status="running",
    )
    try:
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"启动采集失败: {str(e)}")

    TASK_STORE[task_id] = {
        "task_id": task_id,
        "source": payload.source,
        "keywords": payload.keywords,
        "max_count": payload.max_count,
        "log_id": log_entry.id,
        "status": "running",
        "total": 0,
        "success": 0,
        "failed": 0,
        "started_at": log_entry.started_at,
    }

    return CommonResponse(data=CrawlTaskResponse(
        task_id=task_id,
        source=payload.source,
        status="running",
        started_at=log_entry.started_at,
    ).model_dump())


@router.get("/status/{task_id}", response_model=CommonResponse, summary="查询任务状态")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """根据 task_id 查询任务状态

    - 内存中的临时任务或已持久化的日志
    """
    if task_id in TASK_STORE:
        return CommonResponse(data=TASK_STORE[task_id])

    # 回退到日志表
    log_entry = db.query(DataCrawlLog).filter(
        DataCrawlLog.id == task_id.split("_")[-1]
    ).first()
    if not log_entry:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    return CommonResponse(data={
        "task_id": task_id,
        "source": log_entry.source,
        "status": log_entry.status,
        "total": log_entry.total_count,
        "success": log_entry.success_count,
        "failed": log_entry.failed_count,
        "started_at": log_entry.started_at.isoformat() if log_entry.started_at else None,
        "finished_at": log_entry.finished_at.isoformat() if log_entry.finished_at else None,
    })


@router.get("/logs", response_model=CommonResponse, summary="采集日志列表")
def list_crawl_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """分页查询历史采集日志"""
    q = db.query(DataCrawlLog)
    if source:
        q = q.filter(DataCrawlLog.source == source)
    total = q.count()
    items = q.order_by(desc(DataCrawlLog.started_at)).offset((page - 1) * page_size).limit(page_size).all()
    data = [
        CrawlLogItem(
            id=r.id,
            source=r.source or "",
            task_type=r.task_type or "incremental",
            started_at=r.started_at or datetime.now(),
            finished_at=r.finished_at,
            total_count=r.total_count or 0,
            success_count=r.success_count or 0,
            failed_count=r.failed_count or 0,
            status=r.status or "running",
            error_message=r.error_message,
        ).model_dump()
        for r in items
    ]
    return CommonResponse(data=PageResponse(
        items=data,
        pagination=Pagination(page=page, page_size=page_size, total=total),
    ).model_dump())


@router.post("/mock", response_model=CommonResponse, summary="生成模拟数据")
def generate_mock_data(payload: MockDataRequest, db: Session = Depends(get_db)):
    """一键生成演示用的 JD、简历、岗位卡片

    - 用于系统演示与压力测试
    - 数据具有随机性，但保持合理的结构
    """
    companies = ["字节跳动", "腾讯", "阿里巴巴", "美团", "京东", "百度", "小米", "华为", "网易", "滴滴"]
    locations = ["北京", "上海", "深圳", "杭州", "广州", "成都"]
    categories = ["前端", "后端", "算法", "数据", "产品", "运维", "测试"]
    levels = ["初级", "中级", "高级", "资深"]
    skills_pool = ["Python", "Java", "Go", "JavaScript", "TypeScript", "Vue", "React",
                   "Docker", "Kubernetes", "MySQL", "Redis", "MongoDB", "Elasticsearch",
                   "机器学习", "深度学习", "TensorFlow", "PyTorch", "NLP", "推荐系统", "图神经网络"]

    random.seed(42)
    jd_created = 0
    role_created = 0
    resume_created = 0

    try:
        # 生成 JD
        for i in range(payload.jd_count):
            skills = random.sample(skills_pool, k=min(6, len(skills_pool)))
            record = JDRecord(
                jd_id=f"jd_mock_{uuid.uuid4().hex[:12]}",
                source=random.choice(["拉勾", "Boss直聘", "猎聘", "LinkedIn"]),
                company=random.choice(companies),
                title=f"{random.choice(categories)}工程师",
                category=random.choice(categories),
                level=random.choice(levels),
                location=random.choice(locations),
                salary_range=f"{random.randint(15, 50)}K-{random.randint(50, 100)}K",
                raw_text=f"岗位职责：负责{random.choice(categories)}相关开发，要求掌握{','.join(skills)}",
                skills=skills,
                published_at=datetime.now() - timedelta(days=random.randint(0, 365)),
                is_processed=1,
                credibility_score=round(random.uniform(0.5, 1.0), 2),
            )
            db.add(record)
            jd_created += 1

        # 生成岗位卡片
        for i in range(payload.role_count):
            name = f"{random.choice(categories)}专家-{uuid.uuid4().hex[:6]}"
            record = JobRoleCard(
                role_id=f"role_{uuid.uuid4().hex[:12]}",
                name=name,
                category=random.choice(categories),
                level=random.choice(levels),
                core_responsibilities=["负责系统设计", "主导技术选型", "团队协作"],
                required_skills=[
                    {"name": s, "weight": round(random.uniform(0.5, 1.0), 2)}
                    for s in random.sample(skills_pool, k=4)
                ],
                preferred_skills=[
                    {"name": s, "weight": round(random.uniform(0.3, 0.8), 2)}
                    for s in random.sample(skills_pool, k=2)
                ],
                confidence=round(random.uniform(0.5, 1.0), 2),
                evidence_sources=[f"jd_mock_{i}" for i in range(random.randint(2, 6))],
                is_new=1 if random.random() < 0.3 else 0,
                is_reviewed=0,
            )
            db.add(record)
            role_created += 1

        # 简历生成（仅插入记录，文件不上传）
        for i in range(payload.resume_count):
            from app.models.resume import ResumeRecord
            skills = random.sample(skills_pool, k=min(5, len(skills_pool)))
            record = ResumeRecord(
                resume_id=f"resume_mock_{uuid.uuid4().hex[:12]}",
                file_name=f"mock_resume_{i}.pdf",
                file_type="pdf",
                file_size=random.randint(100000, 500000),
                file_path=f"./data/resumes/mock_{i}.pdf",
                name=f"候选人{i}",
                skills=[
                    {"name": s, "standard_name": s, "level": random.choice(["beginner", "intermediate", "advanced"])}
                    for s in skills
                ],
                parse_status="success",
            )
            db.add(record)
            resume_created += 1

        db.commit()
    except Exception as e:
        db.rollback()
        log.error(f"生成模拟数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成模拟数据失败: {str(e)}")

    return CommonResponse(data={
        "jd_created": jd_created,
        "role_created": role_created,
        "resume_created": resume_created,
    })
