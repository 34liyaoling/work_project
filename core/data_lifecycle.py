"""数据生命周期管理器 - 置信度衰减、自动归档、新鲜度评分"""

import logging
from datetime import datetime, timezone
from typing import Optional
from core.graph_service import get_graph_service

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_LIFETIME_DAYS = 90            # 默认数据寿命（天）
ARCHIVE_AFTER_DAYS = 90               # 超过此天数归档
STALE_WARNING_DAYS = 30               # 超过此天数标记为陈旧
DECAY_FACTOR = 0.15                   # 每月置信度衰减系数
FRESHNESS_HALF_LIFE = 45              # 新鲜度半衰期（天）


class DataLifecycleManager:
    """数据生命周期管理器

    功能：
    1. 置信度衰减：数据越旧，置信度越低
    2. 岗位自动归档：超期岗位标记为 archived
    3. 新鲜度评分：为每个节点计算 0-1 的新鲜度分数
    4. 生命周期状态机：active → stale → candidate → archived
    """

    def __init__(self):
        self.graph = get_graph_service()

    # ==================== 新鲜度评分 ====================

    def compute_freshness(self, last_updated_str: Optional[str]) -> float:
        """计算数据新鲜度，返回 0.0-1.0

        使用半衰期衰减模型：45天后新鲜度降到0.5
        """
        if not last_updated_str:
            return 0.3

        try:
            if isinstance(last_updated_str, str):
                last_updated = datetime.fromisoformat(last_updated_str.replace("Z", "+00:00"))
            else:
                last_updated = last_updated_str

            now = datetime.now(timezone.utc)
            age_days = (now - last_updated).days
            if age_days < 0:
                age_days = 0

            # 半衰期衰减模型
            freshness = 2 ** (-age_days / FRESHNESS_HALF_LIFE)
            return round(max(0.0, min(1.0, freshness)), 4)
        except Exception as e:
            logger.debug(f"新鲜度计算失败: {e}")
            return 0.5

    def compute_decayed_confidence(self, base_confidence: float,
                                    last_updated_str: Optional[str]) -> float:
        """计算衰减后的置信度

        公式：decayed = base × (1 - DECAY_FACTOR)^(months_old)
        """
        if not last_updated_str:
            return base_confidence * 0.5

        try:
            if isinstance(last_updated_str, str):
                last_updated = datetime.fromisoformat(last_updated_str.replace("Z", "+00:00"))
            else:
                last_updated = last_updated_str

            now = datetime.now(timezone.utc)
            age_days = max(0, (now - last_updated).days)
            months_old = age_days / 30.0

            decayed = base_confidence * ((1 - DECAY_FACTOR) ** months_old)
            return round(max(0.1, min(base_confidence, decayed)), 4)
        except Exception as e:
            logger.debug(f"置信度衰减计算失败: {e}")
            return base_confidence * 0.5

    # ==================== 生命周期判断 ====================

    def determine_lifecycle(self, last_updated_str: Optional[str]) -> str:
        """根据更新时间判断生命周期状态

        active (0-30天): 数据新鲜，正常参与匹配
        stale (30-90天): 数据偏旧，标注陈旧
        candidate (90-180天): 数据很旧，不参与匹配
        archived (180天+): 数据过期，归档不可见
        """
        if not last_updated_str:
            return "stale"

        try:
            if isinstance(last_updated_str, str):
                last_updated = datetime.fromisoformat(last_updated_str.replace("Z", "+00:00"))
            else:
                last_updated = last_updated_str

            now = datetime.now(timezone.utc)
            age_days = max(0, (now - last_updated).days)

            if age_days <= 30:
                return "active"
            elif age_days <= 90:
                return "stale"
            elif age_days <= 180:
                return "candidate"
            else:
                return "archived"
        except Exception as e:
            logger.debug(f"生命周期判断失败: {e}")
            return "stale"

    def should_archive(self, last_updated_str: Optional[str]) -> bool:
        """判断是否应该归档"""
        status = self.determine_lifecycle(last_updated_str)
        return status in ("candidate", "archived")

    # ==================== 批量处理 ====================

    def refresh_job_lifecycle(self, job_title: str = None) -> dict:
        """刷新岗位的生命周期状态

        对指定岗位（或所有岗位）重新计算生命周期状态
        """
        if not self.graph.is_connected:
            self.graph.connect()
        if not self.graph.is_connected:
            return {"success": False, "error": "Neo4j未连接"}

        if job_title:
            cypher = """
            MATCH (j:Job {title: $title})
            RETURN j.title AS title, j.last_updated AS last_updated,
                   coalesce(j.status, 'active') AS status
            """
            params = {"title": job_title}
        else:
            cypher = """
            MATCH (j:Job)
            WITH j, coalesce(j.status, 'active') AS effective_status
            WHERE effective_status <> 'archived'
            RETURN j.title AS title, j.last_updated AS last_updated,
                   effective_status AS status
            """
            params = {}

        try:
            with self.graph._get_session() as session:
                jobs = list(session.run(cypher, **params))
        except Exception as e:
            logger.error(f"查询岗位失败: {e}")
            return {"success": False, "error": str(e)}

        results = {"checked": len(jobs), "updated": 0, "archived": 0}
        for job in jobs:
            last_updated = job.get("last_updated")
            lifecycle = self.determine_lifecycle(str(last_updated) if last_updated else None)

            if lifecycle != job.get("status", ""):
                try:
                    if lifecycle == "archived":
                        # 归档：设置为candidate状态，不直接删除
                        self._update_job_status(job["title"], "candidate")
                        results["archived"] += 1
                    else:
                        self._update_job_status(job["title"], "active")
                    results["updated"] += 1
                except Exception as e:
                    logger.warning(f"岗位状态更新失败 [{job['title']}]: {e}")

        if results["archived"] > 0:
            logger.info(f"生命周期刷新: 检查{results['checked']}个, "
                        f"更新{results['updated']}个, "
                        f"归档{results['archived']}个")
        return results

    def _update_job_status(self, title: str, status: str):
        """更新岗位状态"""
        cypher = """
        MATCH (j:Job {title: $title})
        SET j.status = $status,
            j.updated_at = datetime()
        """
        with self.graph._get_session() as session:
            session.run(cypher, title=title, status=status)

    def get_freshness_summary(self) -> dict:
        """获取数据新鲜度概览"""
        if not self.graph.is_connected:
            self.graph.connect()
        if not self.graph.is_connected:
            return {"error": "Neo4j未连接"}

        cypher = """
        MATCH (j:Job)
        RETURN j.title AS title, j.last_updated AS last_updated,
               j.status AS status
        """
        try:
            with self.graph._get_session() as session:
                jobs = list(session.run(cypher))
        except Exception as e:
            logger.error(f"查询岗位新鲜度失败: {e}")
            return {"error": str(e)}

        buckets = {"active": 0, "stale": 0, "candidate": 0, "archived": 0}
        total_freshness = 0.0
        job_details = []

        for job in jobs:
            last_updated = job.get("last_updated")
            lu_str = str(last_updated) if last_updated else None
            lifecycle = self.determine_lifecycle(lu_str)
            freshness = self.compute_freshness(lu_str)
            buckets[lifecycle] = buckets.get(lifecycle, 0) + 1
            total_freshness += freshness

            job_details.append({
                "title": job["title"],
                "lifecycle": lifecycle,
                "freshness": freshness,
                "last_updated": lu_str[:19] if lu_str else "unknown",
            })

        job_count = len(jobs) or 1
        return {
            "total_jobs": len(jobs),
            "avg_freshness": round(total_freshness / job_count, 4),
            "lifecycle_distribution": buckets,
            "by_job": sorted(job_details, key=lambda x: x["freshness"]),
        }

    def get_stale_jobs(self, min_age_days: int = STALE_WARNING_DAYS) -> list[dict]:
        """获取超过指定天数未更新的陈旧岗位"""
        if not self.graph.is_connected:
            self.graph.connect()
        if not self.graph.is_connected:
            return []

        cypher = """
        MATCH (j:Job)
        WITH j, coalesce(j.status, 'active') AS effective_status
        WHERE j.last_updated IS NOT NULL
          AND j.last_updated < datetime() - duration($duration)
          AND effective_status <> 'archived'
        RETURN j.title AS title, j.last_updated AS last_updated,
               j.status AS status, j.source AS source
        ORDER BY j.last_updated ASC
        """
        duration_str = f"P{min_age_days}D"
        try:
            with self.graph._get_session() as session:
                records = list(session.run(cypher, duration=duration_str))
                results = []
                for r in records:
                    lu = r.get("last_updated")
                    results.append({
                        "title": r["title"],
                        "last_updated": str(lu)[:19] if lu else "unknown",
                        "status": r.get("status", ""),
                        "source": r.get("source", ""),
                        "freshness": self.compute_freshness(str(lu) if lu else None),
                        "recommendation": "建议重新采集" if self.should_archive(str(lu) if lu else None) else "可继续使用",
                    })
                return results
        except Exception as e:
            logger.error(f"查询陈旧岗位失败: {e}")
            return []

    def archive_stale_jobs(self, force_archive_days: int = ARCHIVE_AFTER_DAYS) -> dict:
        """归档超期岗位

        将超过 force_archive_days 天未更新的岗位标记为 candidate
        """
        stale = self.get_stale_jobs(min_age_days=force_archive_days)
        archived_count = 0

        for job in stale:
            if job["recommendation"] == "建议重新采集" and job.get("status") != "candidate":
                try:
                    self._update_job_status(job["title"], "candidate")
                    archived_count += 1
                    logger.info(f"岗位已归档: {job['title']}")
                except Exception as e:
                    logger.warning(f"归档失败 [{job['title']}]: {e}")

        return {
            "checked": len(stale),
            "archived": archived_count,
            "message": f"检查了{len(stale)}个陈旧岗位，归档了{archived_count}个",
        }
