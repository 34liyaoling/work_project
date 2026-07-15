"""人岗匹配 API

提供两种匹配方式：与具体 JD 匹配 / 与岗位方向匹配（Top-N）。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.schemas import (
    CommonResponse,
    GapSkillItem,
    MatchBreakdownItem,
    MatchJDRequest,
    MatchResultResponse,
    MatchRoleRequest,
    PageResponse,
    Pagination,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.logger import log
from app.core.neo4j_db import neo4j_client
from app.models.jd import JDRecord
from app.models.resume import MatchRecord, ResumeRecord

router = APIRouter()


def _build_resume_skill_set(resume: ResumeRecord) -> Dict[str, Dict[str, Any]]:
    """将简历技能转换为标准名 -> 详情 的字典"""
    skill_set: Dict[str, Dict[str, Any]] = {}
    for s in (resume.skills or []):
        name = s.get("standard_name") or s.get("name")
        if not name:
            continue
        skill_set[name] = s
    return skill_set


def _query_required_skills(target_id: str, target_type: str) -> List[Dict[str, Any]]:
    """从图谱中查询目标岗位的必备/加分技能

    - target_type='jd' 时仅按 JD 文本提取的 skills 字段使用
    - target_type='role' 时通过 Cypher 查询 JobRole
    """
    if target_type == "role":
        session = neo4j_client.get_session()
        if not session:
            return []
        try:
            cypher = """
            MATCH (j:JobRole {name: $name})
            OPTIONAL MATCH (j)-[r:REQUIRES]->(s:Skill)
            RETURN s.name AS name, r.weight AS weight, 'required' AS type
            """
            result = session.run(cypher, {"name": target_id})
            return [dict(record) for record in result]
        except Exception as e:
            log.warning(f"查询岗位技能失败: {e}")
            return []
        finally:
            session.close()
    return []


def _compute_match(
    resume_skill_set: Dict[str, Dict[str, Any]],
    target_skills: List[Dict[str, Any]],
    weights: Dict[str, float],
) -> Dict[str, Any]:
    """计算匹配结果（多维度）"""
    if not target_skills:
        return {
            "overall_score": 0.0,
            "required_score": 0.0,
            "preferred_score": 0.0,
            "depth_score": 0.0,
            "domain_score": 0.0,
            "breakdown": [],
            "gap_skills": [],
            "matched": [],
        }

    required = [s for s in target_skills if s.get("type") == "required" or True]
    matched = []
    missing = []

    for t in target_skills:
        t_name = t.get("name")
        if not t_name:
            continue
        if t_name in resume_skill_set:
            matched.append({
                "skill": t_name,
                "weight": t.get("weight", 1.0),
                "resume_level": resume_skill_set[t_name].get("level", "intermediate"),
            })
        else:
            missing.append({
                "skill": t_name,
                "weight": t.get("weight", 1.0),
                "importance": t.get("weight", 1.0),
            })

    total_weight = sum(s.get("weight", 1.0) for s in target_skills) or 1.0
    matched_weight = sum(m["weight"] for m in matched)
    required_score = matched_weight / total_weight

    # 技能深度评估：简历 level 映射得分
    level_score_map = {"beginner": 0.4, "intermediate": 0.7, "advanced": 1.0}
    depth_score = 0.0
    if matched:
        depth_score = sum(level_score_map.get(m["resume_level"], 0.5) * m["weight"] for m in matched) / total_weight

    # 领域契合度：根据技能 category 一致性
    domain_score = min(1.0, 0.5 + 0.1 * len(matched))

    preferred_score = min(1.0, required_score * 0.9 + 0.1)

    overall = (
        weights.get("required", settings.W_REQUIRED) * required_score
        + weights.get("preferred", settings.W_PREFERRED) * preferred_score
        + weights.get("depth", settings.W_DEPTH) * depth_score
        + weights.get("domain", settings.W_DOMAIN) * domain_score
    )

    breakdown = [
        MatchBreakdownItem(
            dimension="必备技能",
            score=required_score,
            weight=weights.get("required", settings.W_REQUIRED),
            matched_skills=[m["skill"] for m in matched],
            missing_skills=[m["skill"] for m in missing],
        ).model_dump(),
        MatchBreakdownItem(
            dimension="技能深度",
            score=depth_score,
            weight=weights.get("depth", settings.W_DEPTH),
        ).model_dump(),
        MatchBreakdownItem(
            dimension="领域契合",
            score=domain_score,
            weight=weights.get("domain", settings.W_DOMAIN),
        ).model_dump(),
    ]

    gap_skills = [
        GapSkillItem(
            skill_name=m["skill"],
            status="missing",
            importance=m["importance"],
            suggestion=f"建议通过在线课程或项目实践学习 {m['skill']}",
        ).model_dump()
        for m in missing
    ]

    return {
        "overall_score": round(overall, 4),
        "required_score": round(required_score, 4),
        "preferred_score": round(preferred_score, 4),
        "depth_score": round(depth_score, 4),
        "domain_score": round(domain_score, 4),
        "breakdown": breakdown,
        "gap_skills": gap_skills,
        "matched": [m["skill"] for m in matched],
    }


@router.post("/jd", response_model=CommonResponse, summary="与具体 JD 匹配")
def match_with_jd(payload: MatchJDRequest, db: Session = Depends(get_db)):
    """方式一：与指定 JD 精准匹配"""
    resume = db.query(ResumeRecord).filter(ResumeRecord.resume_id == payload.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail=f"简历 {payload.resume_id} 不存在")
    jd = db.query(JDRecord).filter(JDRecord.jd_id == payload.jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail=f"JD {payload.jd_id} 不存在")

    resume_skill_set = _build_resume_skill_set(resume)
    jd_skills = [
        {"name": s, "weight": 1.0, "type": "required"}
        for s in (jd.skills or [])
    ]

    weights = payload.weights or {
        "required": settings.W_REQUIRED,
        "preferred": settings.W_PREFERRED,
        "depth": settings.W_DEPTH,
        "domain": settings.W_DOMAIN,
    }
    result = _compute_match(resume_skill_set, jd_skills, weights)

    # 持久化匹配结果
    record = MatchRecord(
        resume_id=payload.resume_id,
        target_id=payload.jd_id,
        target_type="jd",
        overall_score=result["overall_score"],
        required_score=result["required_score"],
        preferred_score=result["preferred_score"],
        depth_score=result["depth_score"],
        domain_score=result["domain_score"],
        breakdown=result["breakdown"],
        gap_skills=result["gap_skills"],
        recommendations=[
            f"补齐技能：{g['skill_name']}" for g in result["gap_skills"][:5]
        ],
    )
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception as e:
        db.rollback()
        log.error(f"保存匹配结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")

    return CommonResponse(data=MatchResultResponse(
        match_id=record.id,
        resume_id=record.resume_id,
        target_id=record.target_id,
        target_type=record.target_type,
        target_name=jd.title,
        overall_score=record.overall_score,
        required_score=record.required_score,
        preferred_score=record.preferred_score,
        depth_score=record.depth_score,
        domain_score=record.domain_score,
        breakdown=result["breakdown"],
        gap_skills=result["gap_skills"],
        recommendations=record.recommendations or [],
        learning_path=[],
        created_at=record.created_at or datetime.now(),
    ).model_dump())


@router.post("/role", response_model=CommonResponse, summary="与岗位方向匹配")
def match_with_role(payload: MatchRoleRequest, db: Session = Depends(get_db)):
    """方式二：根据简历与图谱中岗位方向做 Top-N 排名匹配"""
    resume = db.query(ResumeRecord).filter(ResumeRecord.resume_id == payload.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail=f"简历 {payload.resume_id} 不存在")

    resume_skill_set = _build_resume_skill_set(resume)
    weights = payload.weights or {
        "required": settings.W_REQUIRED,
        "preferred": settings.W_PREFERRED,
        "depth": settings.W_DEPTH,
        "domain": settings.W_DOMAIN,
    }

    # 从 Neo4j 拉取所有岗位及其必备技能
    session = neo4j_client.get_session()
    results = []
    if session:
        try:
            cypher = """
            MATCH (j:JobRole)
            OPTIONAL MATCH (j)-[r:REQUIRES]->(s:Skill)
            WITH j, collect({name: s.name, weight: r.weight, type: 'required'}) AS required_skills
            RETURN j.name AS role, j.category AS category, j.level AS level,
                   required_skills
            """
            for record in session.run(cypher):
                role = record["role"]
                skills = [s for s in (record["required_skills"] or []) if s.get("name")]
                if not skills:
                    continue
                m = _compute_match(resume_skill_set, skills, weights)
                results.append({
                    "role": role,
                    "category": record["category"],
                    "level": record["level"],
                    "overall_score": m["overall_score"],
                    "required_score": m["required_score"],
                    "matched_skills": m["matched"],
                    "gap_skills": m["gap_skills"],
                })
        except Exception as e:
            log.warning(f"岗位方向匹配查询失败: {e}")
        finally:
            session.close()

    # 按总分排序
    results.sort(key=lambda x: x["overall_score"], reverse=True)
    top_results = results[:payload.top_n]

    return CommonResponse(data={
        "resume_id": payload.resume_id,
        "top_n": payload.top_n,
        "results": top_results,
    })


@router.get("/{match_id}", response_model=CommonResponse, summary="获取匹配记录")
def get_match(match_id: int, db: Session = Depends(get_db)):
    """根据 match_id 获取单次匹配结果"""
    record = db.query(MatchRecord).filter(MatchRecord.id == match_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"匹配记录 {match_id} 不存在")

    return CommonResponse(data=MatchResultResponse(
        match_id=record.id,
        resume_id=record.resume_id,
        target_id=record.target_id,
        target_type=record.target_type or "jd",
        overall_score=record.overall_score or 0.0,
        required_score=record.required_score or 0.0,
        preferred_score=record.preferred_score or 0.0,
        depth_score=record.depth_score or 0.0,
        domain_score=record.domain_score or 0.0,
        breakdown=record.breakdown or [],
        gap_skills=record.gap_skills or [],
        recommendations=record.recommendations or [],
        learning_path=[],
        created_at=record.created_at or datetime.now(),
    ).model_dump())


@router.get("/", response_model=CommonResponse, summary="匹配记录列表")
def list_matches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    resume_id: Optional[str] = None,
    target_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """分页查询匹配历史"""
    q = db.query(MatchRecord)
    if resume_id:
        q = q.filter(MatchRecord.resume_id == resume_id)
    if target_type:
        q = q.filter(MatchRecord.target_type == target_type)
    total = q.count()
    items = q.order_by(desc(MatchRecord.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    data = [
        {
            "match_id": r.id,
            "resume_id": r.resume_id,
            "target_id": r.target_id,
            "target_type": r.target_type,
            "overall_score": r.overall_score,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in items
    ]
    return CommonResponse(data=PageResponse(
        items=data,
        pagination=Pagination(page=page, page_size=page_size, total=total),
    ).model_dump())
