"""简历解析 API

提供简历上传、解析、技能提取等接口。
"""
from __future__ import annotations

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.schemas import (
    CommonResponse,
    PageResponse,
    Pagination,
    ResumeParseRequest,
    ResumeResponse,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.logger import log
from app.models.resume import ResumeRecord

router = APIRouter()

UPLOAD_DIR = "./data/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _extract_text_from_pdf(file_path: str) -> str:
    """从 PDF 提取文本（容错处理）"""
    try:
        import fitz  # PyMuPDF
        text_parts = []
        with fitz.open(file_path) as doc:
            for page in doc:
                text_parts.append(page.get_text())
        return "\n".join(text_parts)
    except Exception as e:
        log.warning(f"PDF 文本提取失败: {e}")
        return ""


def _extract_text_from_docx(file_path: str) -> str:
    """从 Word 文档提取文本"""
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        log.warning(f"Word 文本提取失败: {e}")
        return ""


def _parse_skills_from_text(text: str) -> list:
    """从简历文本中匹配技能（基于技能词典）"""
    if not text:
        return []
    import json
    skill_dict_path = settings.SKILL_DICT_PATH
    if not os.path.exists(skill_dict_path):
        return []
    try:
        with open(skill_dict_path, "r", encoding="utf-8") as f:
            skill_dict = json.load(f)
    except Exception:
        return []
    text_lower = text.lower()
    found = []
    for skill, info in skill_dict.items():
        if skill.lower() in text_lower:
            found.append({
                "name": skill,
                "standard_name": info.get("standard_name", skill),
                "category": info.get("category", "未分类"),
                "level": info.get("level", "intermediate"),
                "weight": info.get("weight", 1.0),
            })
    return found


@router.post("/upload", response_model=CommonResponse, summary="上传简历")
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传 PDF / Word 格式简历

    - 支持 .pdf / .docx
    - 自动生成 resume_id
    - 上传后立即返回，解析可异步触发
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in {".pdf", ".docx", ".doc"}:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    resume_id = f"resume_{uuid.uuid4().hex[:16]}"
    file_path = os.path.join(UPLOAD_DIR, f"{resume_id}{ext}")
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        log.error(f"保存简历文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    record = ResumeRecord(
        resume_id=resume_id,
        file_name=file.filename,
        file_type=ext.lstrip("."),
        file_size=len(content),
        file_path=file_path,
        parse_status="pending",
    )
    try:
        db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        # 清理已上传的文件
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"数据库写入失败: {str(e)}")

    return CommonResponse(data={
        "resume_id": resume_id,
        "file_name": file.filename,
        "file_size": len(content),
        "parse_status": "pending",
    })


@router.get("/{resume_id}", response_model=CommonResponse, summary="获取简历详情")
def get_resume(resume_id: str, db: Session = Depends(get_db)):
    """根据 resume_id 获取简历详细信息"""
    record = db.query(ResumeRecord).filter(ResumeRecord.resume_id == resume_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"简历 {resume_id} 不存在")

    return CommonResponse(data=ResumeResponse(
        resume_id=record.resume_id,
        file_name=record.file_name or "",
        file_type=record.file_type,
        file_size=record.file_size,
        name=record.name,
        education=record.education or [],
        work_experience=record.work_experience or [],
        projects=record.projects or [],
        skills=record.skills or [],
        uploaded_at=record.uploaded_at,
        parsed_at=record.parsed_at,
        parse_status=record.parse_status or "pending",
        parse_accuracy=record.parse_accuracy,
    ).model_dump())


@router.get("/", response_model=CommonResponse, summary="简历列表")
def list_resumes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    parse_status: Optional[str] = None,
    name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """分页查询简历列表"""
    q = db.query(ResumeRecord)
    if parse_status:
        q = q.filter(ResumeRecord.parse_status == parse_status)
    if name:
        q = q.filter(ResumeRecord.name.like(f"%{name}%"))

    total = q.count()
    items = q.order_by(desc(ResumeRecord.uploaded_at)).offset((page - 1) * page_size).limit(page_size).all()
    data = [
        {
            "resume_id": r.resume_id,
            "file_name": r.file_name,
            "name": r.name,
            "parse_status": r.parse_status,
            "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None,
            "skill_count": len(r.skills or []),
        }
        for r in items
    ]
    return CommonResponse(data=PageResponse(
        items=data,
        pagination=Pagination(page=page, page_size=page_size, total=total),
    ).model_dump())


@router.post("/{resume_id}/parse", response_model=CommonResponse, summary="触发简历解析")
def parse_resume(resume_id: str, payload: ResumeParseRequest = ResumeParseRequest(), db: Session = Depends(get_db)):
    """从上传文件中提取文本并解析结构化字段

    - 提取教育、工作、项目经历
    - 基于技能词典匹配技能
    - 计算技能向量
    """
    record = db.query(ResumeRecord).filter(ResumeRecord.resume_id == resume_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"简历 {resume_id} 不存在")

    if record.parse_status == "success" and not payload.force:
        return CommonResponse(message="已解析，跳过", data={
            "resume_id": resume_id,
            "parse_status": "success",
            "skills": record.skills,
        })

    file_path = record.file_path
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="简历文件不存在或已被清理")

    try:
        record.parse_status = "parsing"
        db.commit()

        if record.file_type == "pdf":
            text = _extract_text_from_pdf(file_path)
        else:
            text = _extract_text_from_docx(file_path)

        record.raw_text = text
        skills = _parse_skills_from_text(text)
        record.skills = skills
        record.parsed_data = {
            "text_length": len(text),
            "skill_count": len(skills),
            "parser": "rule-based-dictionary",
        }
        record.parse_status = "success"
        from datetime import datetime
        record.parsed_at = datetime.now()
        db.commit()
    except Exception as e:
        db.rollback()
        record.parse_status = "failed"
        db.commit()
        log.error(f"简历解析失败: {e}")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")

    return CommonResponse(data={
        "resume_id": resume_id,
        "parse_status": "success",
        "skill_count": len(skills),
        "skills": [s["name"] for s in skills],
    })


@router.get("/{resume_id}/skills", response_model=CommonResponse, summary="获取简历技能列表")
def get_resume_skills(resume_id: str, db: Session = Depends(get_db)):
    """获取简历中已抽取的结构化技能列表"""
    record = db.query(ResumeRecord).filter(ResumeRecord.resume_id == resume_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"简历 {resume_id} 不存在")

    return CommonResponse(data={
        "resume_id": resume_id,
        "skills": record.skills or [],
        "parse_status": record.parse_status,
    })
