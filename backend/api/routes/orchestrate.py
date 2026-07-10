"""编排中心API路由 - 暴露多Agent协作能力"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.schemas.models import ApiResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/orchestrate", tags=["编排中心"])


# ===== 请求/响应模型 =====
class OrchestrateRequest(BaseModel):
    """编排请求"""
    request: str = Field(..., description="用户自然语言请求")
    context: dict = Field(default_factory=dict, description="附加上下文")


class OrchestrateResponse(BaseModel):
    """编排响应"""
    success: bool
    intent: dict
    total_steps: int
    completed_steps: int
    outputs: dict
    quality_summary: dict
    errors: Optional[list] = None


# ===== 编排中心单例 =====
_orchestrator = None
_agents_registered = False


def _get_orchestrator():
    """获取已注册Agent的编排中心单例"""
    global _orchestrator, _agents_registered
    if _orchestrator is None:
        from agents.orchestrator import OrchestratorAgent
        _orchestrator = OrchestratorAgent()

    if not _agents_registered:
        # 注册所有专业Agent
        try:
            from agents.data_collector import DataCollectorAgent
            from agents.graph_builder import GraphBuilderAgent
            from agents.resume_parser import ResumeParserAgent
            from agents.matching_agent import MatchingAgent
            from agents.gap_analyzer import GapAnalyzerAgent
            from agents.job_discovery import JobDiscoveryAgent
            from agents.quality_guardian import QualityGuardianAgent

            for agent_cls in [
                DataCollectorAgent,
                GraphBuilderAgent,
                ResumeParserAgent,
                MatchingAgent,
                GapAnalyzerAgent,
                JobDiscoveryAgent,
                QualityGuardianAgent,
            ]:
                try:
                    instance = agent_cls()
                    _orchestrator.register_agent(instance)
                except Exception as e:
                    logger.warning(f"注册Agent失败 [{agent_cls.__name__}]: {e}")

            _agents_registered = True
            logger.info(f"编排中心已注册 {_orchestrator.agent_registry.__len__()} 个Agent")
        except Exception as e:
            logger.error(f"注册Agent失败: {e}")

    return _orchestrator


# ===== 路由 =====
@router.post("", response_model=ApiResponse)
async def orchestrate(req: OrchestrateRequest):
    """
    编排执行用户自然语言请求

    自动完成：意图识别 → 任务分解 → Agent分配 → 顺序执行 → 结果汇总

    支持的意图类型：
    - resume_analysis: 简历分析
    - job_matching: 岗位匹配
    - gap_analysis: 差距分析
    - job_discovery: 新岗位发现
    - data_collection: 数据采集
    - career_path: 职业规划
    - what_if: What-If模拟
    - qa_question: 问答查询
    - market_analysis: 市场分析
    - graph_operation: 图谱操作
    """
    try:
        orchestrator = _get_orchestrator()
        result = orchestrator.orchestrate(req.request, req.context)

        if not result.get("success"):
            return ApiResponse(
                success=False,
                message=f"编排执行失败: {len(result.get('errors', []))}个步骤失败",
                data=result,
            )

        return ApiResponse(
            success=True,
            message=f"编排执行完成: {result.get('completed_steps', 0)}/{result.get('total_steps', 0)}步骤成功",
            data=result,
        )

    except Exception as e:
        logger.error(f"编排执行失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"编排失败: {str(e)}")


@router.get("/intent", response_model=ApiResponse)
async def analyze_intent(request: str):
    """分析用户请求的意图（不执行，仅识别）"""
    try:
        orchestrator = _get_orchestrator()
        intent = orchestrator._analyze_intent(request)
        sub_tasks = orchestrator._decompose_task(intent, request)

        return ApiResponse(
            success=True,
            message="意图识别完成",
            data={
                "intent": intent,
                "sub_tasks": sub_tasks,
                "agents_available": list(orchestrator.agent_registry.keys()),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"意图分析失败: {str(e)}")


@router.get("/agents", response_model=ApiResponse)
async def list_agents():
    """列出已注册的Agent及其状态"""
    try:
        orchestrator = _get_orchestrator()
        agents_info = []
        for name, agent in orchestrator.agent_registry.items():
            agents_info.append({
                "name": name,
                "description": getattr(agent, "agent_description", ""),
                "version": getattr(agent, "agent_version", "1.0"),
                "stats": agent.get_stats() if hasattr(agent, "get_stats") else {},
            })

        return ApiResponse(
            success=True,
            message=f"已注册 {len(agents_info)} 个Agent",
            data={
                "total_agents": len(agents_info),
                "agents": agents_info,
                "task_history_count": len(orchestrator.task_history),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Agent列表失败: {str(e)}")


@router.get("/history", response_model=ApiResponse)
async def get_history(limit: int = 20):
    """获取编排历史记录"""
    try:
        orchestrator = _get_orchestrator()
        history = orchestrator.task_history[-limit:]
        return ApiResponse(
            success=True,
            message=f"获取 {len(history)} 条历史记录",
            data={
                "total": len(orchestrator.task_history),
                "history": history,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")


# ===== 质量守护接口 =====
@router.post("/quality/check", response_model=ApiResponse)
async def run_quality_check():
    """运行全面质量检查（数据质量+图谱质量+合规）"""
    try:
        from agents.quality_guardian import QualityGuardianAgent
        guardian = QualityGuardianAgent()
        result = guardian.run_full_check()

        return ApiResponse(
            success=True,
            message=f"质量检查完成: 状态={result.get('overall_status', 'unknown')}, 发现{result.get('issues_found', 0)}个问题",
            data=result,
        )
    except Exception as e:
        logger.error(f"质量检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"质量检查失败: {str(e)}")


@router.post("/quality/verify", response_model=ApiResponse)
async def verify_output(output: dict):
    """验证特定输出结果的质量"""
    try:
        from agents.quality_guardian import QualityGuardianAgent
        guardian = QualityGuardianAgent()
        result = guardian.verify_output(output)

        return ApiResponse(
            success=True,
            message=f"输出验证完成: {result.get('verdict', 'unknown')}",
            data=result,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"输出验证失败: {str(e)}")


@router.get("/quality/audit-log", response_model=ApiResponse)
async def get_audit_log(limit: int = 10):
    """获取质量审计日志"""
    try:
        from agents.quality_guardian import QualityGuardianAgent
        guardian = QualityGuardianAgent()
        log = guardian.get_audit_log(limit)

        return ApiResponse(
            success=True,
            message=f"获取 {len(log)} 条审计日志",
            data={"total": len(log), "audit_log": log},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取审计日志失败: {str(e)}")


# ===== Agent记忆管理接口 =====
@router.get("/memory/stats", response_model=ApiResponse)
async def get_memory_stats():
    """获取所有Agent的记忆统计"""
    try:
        from backend.storage import get_db
        db = get_db()
        stats = db.get_agent_memory_stats()

        return ApiResponse(
            success=True,
            message="Agent记忆统计获取成功",
            data=stats,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记忆统计失败: {str(e)}")


@router.get("/memory/{agent_name}", response_model=ApiResponse)
async def get_agent_memory(agent_name: str, task_type: Optional[str] = None, limit: int = 50):
    """获取指定Agent的长期记忆（历史经验）"""
    try:
        from backend.storage import get_db
        db = get_db()
        experiences = db.get_agent_experiences(
            agent_name=agent_name,
            task_type=task_type,
            limit=limit,
        )

        return ApiResponse(
            success=True,
            message=f"获取 {agent_name} 的 {len(experiences)} 条经验",
            data={
                "agent_name": agent_name,
                "task_type_filter": task_type,
                "total": len(experiences),
                "experiences": experiences,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Agent记忆失败: {str(e)}")


@router.get("/memory/{agent_name}/entity/{entity_id}", response_model=ApiResponse)
async def get_entity_memory(agent_name: str, entity_id: str):
    """获取指定Agent跟踪的实体历史"""
    try:
        from backend.storage import get_db
        db = get_db()
        history = db.get_agent_entity_history(agent_name, entity_id)

        if not history:
            return ApiResponse(
                success=False,
                message=f"未找到实体 {entity_id}",
                data=None,
            )

        return ApiResponse(
            success=True,
            message=f"获取实体历史成功",
            data=history,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取实体历史失败: {str(e)}")


# ===== 数据生命周期管理接口 =====
@router.get("/lifecycle/summary", response_model=ApiResponse)
async def get_lifecycle_summary():
    """获取数据生命周期概览（岗位新鲜度分布）"""
    try:
        from core.data_lifecycle import DataLifecycleManager
        mgr = DataLifecycleManager()
        summary = mgr.get_freshness_summary()

        return ApiResponse(
            success=True,
            message="数据生命周期概览获取成功",
            data=summary,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取生命周期概览失败: {str(e)}")


@router.get("/lifecycle/stale", response_model=ApiResponse)
async def get_stale_jobs(days: int = 30):
    """获取超过指定天数未更新的陈旧岗位"""
    try:
        from core.data_lifecycle import DataLifecycleManager
        mgr = DataLifecycleManager()
        stale = mgr.get_stale_jobs(min_age_days=days)

        return ApiResponse(
            success=True,
            message=f"发现 {len(stale)} 个陈旧岗位（超过{days}天未更新）",
            data={"count": len(stale), "stale_jobs": stale},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取陈旧岗位失败: {str(e)}")


@router.post("/lifecycle/refresh", response_model=ApiResponse)
async def refresh_lifecycle():
    """刷新所有岗位的生命周期状态"""
    try:
        from core.data_lifecycle import DataLifecycleManager
        mgr = DataLifecycleManager()
        result = mgr.refresh_job_lifecycle()

        return ApiResponse(
            success=True,
            message=f"生命周期刷新完成: 检查{result.get('checked',0)}个, 归档{result.get('archived',0)}个",
            data=result,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生命周期刷新失败: {str(e)}")


@router.post("/lifecycle/archive", response_model=ApiResponse)
async def archive_stale_jobs(days: int = 90):
    """归档超过指定天数的陈旧岗位"""
    try:
        from core.data_lifecycle import DataLifecycleManager
        mgr = DataLifecycleManager()
        result = mgr.archive_stale_jobs(force_archive_days=days)

        return ApiResponse(
            success=True,
            message=result.get("message", "归档完成"),
            data=result,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"归档失败: {str(e)}")
