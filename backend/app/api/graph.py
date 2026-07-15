"""图谱查询 API

提供岗位/技能节点查询、依赖链、多视图、快照等接口。
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.schemas import (
    CommonResponse,
    GraphData,
    GraphEdge,
    GraphNode,
    GraphSnapshotRequest,
    GraphSnapshotResponse,
)
from app.core.database import get_db
from app.core.logger import log
from app.core.neo4j_db import neo4j_client
from app.models.job_role import GraphChangeLog, GraphSnapshot

router = APIRouter()


def _safe_neo4j_run(cypher: str, params: Optional[dict] = None) -> List[Dict[str, Any]]:
    """安全执行 Cypher，连接失败时返回空"""
    session = neo4j_client.get_session()
    if not session:
        return []
    try:
        result = session.run(cypher, params or {})
        return [dict(record) for record in result]
    except Exception as e:
        log.warning(f"Cypher 执行失败: {e}")
        return []
    finally:
        session.close()


@router.get("/jobrole/{name}", response_model=CommonResponse, summary="获取岗位详情")
def get_jobrole(name: str):
    """获取岗位节点详情及所有关联技能

    - 返回岗位元数据
    - 返回该岗位的必备/加分技能列表（含权重）
    """
    # 查询岗位基本信息
    role_cypher = """
    MATCH (j:JobRole {name: $name})
    OPTIONAL MATCH (j)-[r:REQUIRES]->(s:Skill)
    RETURN j.name AS name,
           j.category AS category,
           j.level AS level,
           j.description AS description,
           collect(DISTINCT {skill: s.name, weight: r.weight, type: 'required'}) AS required_skills
    """
    rows = _safe_neo4j_run(role_cypher, {"name": name})
    if not rows:
        raise HTTPException(status_code=404, detail=f"岗位 {name} 不存在")

    row = rows[0]
    # 查询加分技能
    preferred_cypher = """
    MATCH (j:JobRole {name: $name})-[r:PREFERS]->(s:Skill)
    RETURN s.name AS skill, r.weight AS weight
    """
    preferred = _safe_neo4j_run(preferred_cypher, {"name": name})

    return CommonResponse(data={
        "name": row.get("name"),
        "category": row.get("category"),
        "level": row.get("level"),
        "description": row.get("description"),
        "required_skills": [s for s in (row.get("required_skills") or []) if s.get("skill")],
        "preferred_skills": preferred,
    })


@router.get("/skill/{name}/dependencies", response_model=CommonResponse, summary="技能依赖链")
def get_skill_dependencies(name: str, depth: int = Query(3, ge=1, le=5)):
    """递归获取技能的前置依赖关系

    - depth 控制递归层数
    - 返回包含直接依赖和间接依赖
    """
    cypher = """
    MATCH path = (s:Skill {name: $name})-[:DEPENDS_ON*1..%d]->(dep:Skill)
    RETURN [n IN nodes(path) | n.name] AS chain,
           length(path) AS distance
    ORDER BY distance
    """ % depth
    rows = _safe_neo4j_run(cypher, {"name": name})
    return CommonResponse(data={
        "skill": name,
        "depth": depth,
        "dependencies": rows,
    })


@router.get("/skill/{name}/related_jobs", response_model=CommonResponse, summary="通过技能找相关岗位")
def get_related_jobs(name: str, top_n: int = Query(10, ge=1, le=50)):
    """根据技能反向查询关联岗位，按相关度排序"""
    cypher = """
    MATCH (j:JobRole)-[r:REQUIRES|PREFERS]->(s:Skill {name: $name})
    RETURN j.name AS role, j.category AS category, j.level AS level,
           type(r) AS relation, r.weight AS weight
    ORDER BY r.weight DESC
    LIMIT $top_n
    """
    rows = _safe_neo4j_run(cypher, {"name": name, "top_n": top_n})
    return CommonResponse(data={
        "skill": name,
        "related_jobs": rows,
    })


@router.get("/view/{view_type}", response_model=CommonResponse, summary="多视图查询")
def graph_view(view_type: str, limit: int = Query(200, ge=10, le=1000)):
    """根据视图类型返回图谱子集

    - technology_stack: 按技术栈分组
    - level: 按级别（初级/中级/高级）分组
    - domain: 按领域分组
    """
    cypher_map = {
        "technology_stack": """
            MATCH (s:Skill)
            RETURN s.name AS name, s.category AS group_key, s.popularity AS popularity
            ORDER BY s.popularity DESC LIMIT $limit
        """,
        "level": """
            MATCH (j:JobRole)
            RETURN j.name AS name, j.level AS group_key, 1.0 AS popularity
            ORDER BY j.name LIMIT $limit
        """,
        "domain": """
            MATCH (s:Skill)
            WHERE s.category IS NOT NULL
            RETURN s.name AS name, s.category AS group_key, s.popularity AS popularity
            ORDER BY s.popularity DESC LIMIT $limit
        """,
    }
    if view_type not in cypher_map:
        raise HTTPException(status_code=400, detail=f"不支持的视图类型: {view_type}")
    rows = _safe_neo4j_run(cypher_map[view_type], {"limit": limit})
    return CommonResponse(data={
        "view_type": view_type,
        "items": rows,
    })


@router.get("/timeline/{skill_name}", response_model=CommonResponse, summary="技能变化时间线")
def skill_timeline(skill_name: str, db: Session = Depends(get_db)):
    """从变更日志中获取该技能的历史演化"""
    records = db.query(GraphChangeLog).filter(
        GraphChangeLog.node_name == skill_name
    ).order_by(desc(GraphChangeLog.created_at)).limit(200).all()
    timeline = [
        {
            "date": r.created_at.isoformat() if r.created_at else None,
            "change_type": r.change_type,
            "change_detail": r.change_detail or {},
            "confidence": r.confidence or 0.0,
        }
        for r in records
    ]
    return CommonResponse(data={
        "skill_name": skill_name,
        "timeline": timeline,
    })


@router.get("/export", response_model=CommonResponse, summary="导出图谱数据")
def export_graph(view_type: str = Query("default", description="default/technology_stack/level/domain")):
    """导出图谱数据为 G6 可消费的 JSON 结构"""
    nodes_cypher = "MATCH (n) RETURN n, labels(n) AS labels LIMIT 500"
    edges_cypher = "MATCH (a)-[r]->(b) RETURN a.name AS source, b.name AS target, type(r) AS relation, r.weight AS weight LIMIT 1000"

    raw_nodes = _safe_neo4j_run(nodes_cypher)
    raw_edges = _safe_neo4j_run(edges_cypher)

    nodes = []
    for r in raw_nodes:
        n = r.get("n") or {}
        labels = r.get("labels") or []
        node_type = labels[0].lower() if labels else "unknown"
        nodes.append(GraphNode(
            id=n.get("name", ""),
            label=n.get("name", ""),
            type=node_type,
            category=n.get("category"),
            level=n.get("level"),
            popularity=float(n.get("popularity") or 0.0),
            properties={k: v for k, v in n.items() if k not in {"name", "category", "level", "popularity"}},
        ).model_dump())

    edges = []
    for r in raw_edges:
        edges.append(GraphEdge(
            source=r.get("source", ""),
            target=r.get("target", ""),
            relation=r.get("relation", "related_to"),
            weight=float(r.get("weight") or 1.0),
        ).model_dump())

    return CommonResponse(data=GraphData(
        nodes=nodes,
        edges=edges,
        metadata={"view_type": view_type, "exported_at": str(uuid.uuid1())},
    ).model_dump())


@router.post("/snapshot", response_model=CommonResponse, summary="创建图谱快照")
def create_snapshot(payload: GraphSnapshotRequest, db: Session = Depends(get_db)):
    """将当前图谱状态保存为快照，便于回滚"""
    snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
    nodes_cypher = "MATCH (n) RETURN n, labels(n) AS labels"
    edges_cypher = "MATCH (a)-[r]->(b) RETURN a.name AS source, b.name AS target, type(r) AS relation, r.weight AS weight"
    nodes = _safe_neo4j_run(nodes_cypher)
    edges = _safe_neo4j_run(edges_cypher)

    snapshot = GraphSnapshot(
        snapshot_id=snapshot_id,
        description=payload.description,
        node_count=len(nodes),
        edge_count=len(edges),
        snapshot_data={"nodes": nodes, "edges": edges},
    )
    try:
        db.add(snapshot)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"快照保存失败: {str(e)}")

    return CommonResponse(data=GraphSnapshotResponse(
        snapshot_id=snapshot_id,
        description=payload.description,
        node_count=len(nodes),
        edge_count=len(edges),
        created_at=snapshot.created_at,
    ).model_dump())


@router.post("/snapshot/{snapshot_id}/restore", response_model=CommonResponse, summary="恢复图谱快照")
def restore_snapshot(snapshot_id: str, db: Session = Depends(get_db)):
    """从快照恢复图谱（删除现有节点+边后重写）"""
    snapshot = db.query(GraphSnapshot).filter(GraphSnapshot.snapshot_id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"快照 {snapshot_id} 不存在")

    snapshot_data = snapshot.snapshot_data or {}
    nodes = snapshot_data.get("nodes", [])
    edges = snapshot_data.get("edges", [])

    # 简化恢复：清空当前图谱并重建
    clear_cypher = "MATCH (n) DETACH DELETE n"
    _safe_neo4j_run(clear_cypher)

    for n in nodes:
        node = n.get("n") or {}
        labels = n.get("labels") or ["Node"]
        label = labels[0] if labels else "Node"
        props = ", ".join([f"{k}: ${k}" for k in node.keys()])
        if not props:
            continue
        cypher = f"MERGE (n:{label} {{name: $name}}) SET n += {{{props}}}"
        _safe_neo4j_run(cypher, node)

    for e in edges:
        cypher = f"""
        MERGE (a {{name: $source}})
        MERGE (b {{name: $target}})
        MERGE (a)-[r:{e.get('relation', 'RELATED')}]->(b)
        SET r.weight = $weight
        """
        _safe_neo4j_run(cypher, {
            "source": e.get("source"),
            "target": e.get("target"),
            "weight": e.get("weight", 1.0),
        })

    return CommonResponse(data={
        "snapshot_id": snapshot_id,
        "restored_nodes": len(nodes),
        "restored_edges": len(edges),
    })
