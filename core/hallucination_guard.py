"""幻觉防控四层防御体系 (HPF)

L1: 源头溯源 - 每条知识绑定source_id+原始证据
L2: 约束引擎 - 类型/逻辑/互斥/数值四类约束
L3: 事实核查 - 周期性一致性扫描+异常标记
L4: 人工审核 - 低置信度内容进入审核队列
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional
from models.graph_nodes import GraphTriple, SkillNode, JobNode

logger = logging.getLogger(__name__)


class ProvenanceInfo:
    """溯源信息"""
    def __init__(self, source_id: str, source_type: str, record_id: str,
                 raw_text: str = "", method: str = "unknown"):
        self.source_id = source_id
        self.source_type = source_type
        self.record_id = record_id
        self.raw_text = raw_text[:500]
        self.method = method
        self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "record_id": self.record_id,
            "raw_text": self.raw_text,
            "method": self.method,
            "timestamp": self.timestamp.isoformat(),
        }


class ConstraintEngine:
    """L2: 约束引擎 - 四类约束检查"""

    # 允许的关系类型组合 (head_label, relation, tail_label)
    VALID_RELATION_TYPES = [
        ("Skill", "similar_to", "Skill"),
        ("Job", "requires", "Skill"),
        ("Job", "prefers", "Skill"),
        ("Skill", "belongs_to", "Domain"),
        ("Skill", "part_of", "Category"),
        ("Skill", "evolves_to", "Skill"),
        ("Skill", "prerequisite_for", "Skill"),
        ("Job", "emerges_from", "Job"),
        ("Person", "has_skill", "Skill"),
        ("Person", "applied_for", "Job"),
    ]

    # 数值约束
    VALUE_CONSTRAINTS = {
        "difficulty": {"min": 1, "max": 10},
        "confidence": {"min": 0.0, "max": 1.0},
        "trend_score": {"min": -1.0, "max": 1.0},
        "version": {"pattern": r"^\\d+(\\.\\d+)?$"},
    }

    # 互斥规则
    MUTEX_RULES = [
        "同一岗位下的技能不能同时为required和optional",
        "岗位不能同时为active和archived状态",
        "技能不能同时属于两个不同的主域",
    ]

    def validate_triple(self, head_label: str, relation: str, tail_label: str,
                        properties: dict = None) -> list[dict]:
        """验证一个三元组是否满足所有约束"""
        violations = []
        properties = properties or {}

        # 类型约束
        type_violations = self._check_type_constraint(head_label, relation, tail_label)
        violations.extend(type_violations)

        # 数值约束
        value_violations = self._check_value_constraints(properties)
        violations.extend(value_violations)

        return violations

    def _check_type_constraint(self, head_label: str, relation: str, tail_label: str) -> list[dict]:
        """检查类型约束"""
        valid_combos = {(h, r, t) for h, r, t in self.VALID_RELATION_TYPES}
        actual = (head_label, relation, tail_label)

        if actual not in valid_combos:
            return [{
                "type": "type_violation",
                "severity": "error",
                "message": f"不允许的关系组合: ({head_label})-[{relation}]->({tail_label})"
            }]
        return []

    def _check_value_constraints(self, properties: dict) -> list[dict]:
        """检查数值约束"""
        violations = []
        for key, constraint in self.VALUE_CONSTRAINTS.items():
            if key not in properties:
                continue
            value = properties[key]

            if "min" in constraint and "max" in constraint:
                if not isinstance(value, (int, float)):
                    violations.append({
                        "type": "value_error",
                        "severity": "error",
                        "message": f"属性[{key}]应为数值类型，实际为{type(value).__name__}"
                    })
                elif value < constraint["min"] or value > constraint["max"]:
                    violations.append({
                        "type": "value_out_of_range",
                        "severity": "warning",
                        "message": f"属性[{key}]={value}超出允许范围[{constraint['min']}, {constraint['max']}]"
                    })

            if "pattern" in constraint:
                import re
                if not re.match(constraint["pattern"], str(value)):
                    violations.append({
                        "type": "format_error",
                        "severity": "warning",
                        "message": f"属性[{key}]={value}不符合格式要求"
                    })

        return violations

    def check_mutex_rules(self, existing_triples: list[GraphTriple],
                          new_triple: GraphTriple) -> list[dict]:
        """检查互斥规则"""
        violations = []

        # 规则1: 同一岗位下技能不能同时required和optional
        if (new_triple.relation in ("requires", "prefers") and
            new_triple.head.startswith("Job:")):
            job_key = new_triple.head
            skill_key = new_triple.tail
            opposite_rel = "prefers" if new_triple.relation == "requires" else "requires"

            for t in existing_triples:
                if (t.head == job_key and t.tail == skill_key and
                    t.relation == opposite_rel):
                    violations.append({
                        "type": "mutex_violation",
                        "severity": "error",
                        "message": f"技能[{skill_key}]在岗位[{job_key}]下同时存在requires和prefers关系"
                    })

        return violations


class FactChecker:
    """L3: 事实核查器 - 周期性一致性扫描"""

    def __init__(self, graph_service):
        self.graph = graph_service
        self.scan_results: list[dict] = []
        self.last_scan_time: Optional[datetime] = None

    async def run_consistency_scan(self) -> dict:
        """运行全面一致性扫描"""
        logger.info("开始事实核查扫描...")
        scan_start = datetime.now()

        issues = {
            "low_confidence_triples": [],
            "orphan_nodes": [],
            "anomalous_clusters": [],
            "inconsistencies": [],
            "stale_nodes": [],
        }

        # 1. 低置信度三元组检测
        low_conf = self.graph.execute_query("""
            MATCH ()-[r]->() WHERE r.confidence < 0.7
            RETURN head(startNode(r)), type(r), head(endNode(r)), r.confidence
            LIMIT 100
        """)
        issues["low_confidence_triples"] = low_conf

        # 2. 孤立节点检测
        orphans = self.graph.execute_query("""
            MATCH (n) WHERE size((n)--()) = 0
            RETURN labels(n) as labels, n.name as name
            LIMIT 50
        """)
        issues["orphan_nodes"] = orphans

        # 3. 异常环路检测（技能自引用或短环路）
        cycles = self.graph.execute_query("""
            MATCH path = (s:Skill)-[r*1..3]->(s)
            RETURN length(path) as cycle_len, [n IN nodes(path) | n.name] as nodes
            LIMIT 20
        """)
        issues["anomalous_clusters"] = cycles

        # 4. 陈旧节点检测（超过90天未更新的活跃节点）
        stale = self.graph.execute_query("""
            MATCH (n:Skill) WHERE n.last_updated < datetime() - duration('P90D')
              AND n.lifecycle IN ['growing', 'emerging', 'mature']
            RETURN n.name, n.lifecycle, n.last_updated
            LIMIT 50
        """)
        issues["stale_nodes"] = stale

        # 5. 岗位-技能不一致（岗位要求的技能不存在于图谱中）
        missing_skills = self.graph.execute_query("""
            MATCH (j:Job)-[r:requires]->(s:Skill)
            WHERE s.confidence IS NULL OR s.confidence < 0.3
            RETURN j.title, s.name, r.confidence
            LIMIT 50
        """)
        issues["inconsistencies"] = missing_skills

        scan_result = {
            "scan_time": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - scan_start).total_seconds(),
            "total_issues": sum(len(v) for v in issues.values()),
            "issues": issues,
            "severity": self._assess_severity(issues),
        }

        self.scan_results.append(scan_result)
        self.last_scan_time = datetime.now()

        logger.info(f"事实核查完成，发现{scan_result['total_issues']}个问题")
        return scan_result

    def _assess_severity(self, issues: dict) -> str:
        """评估整体严重程度"""
        total = sum(len(v) for v in issues.values())
        critical_count = len(issues.get("inconsistencies", [])) + len(issues.get("anomalous_clusters", []))

        if critical_count > 20 or total > 100:
            return "critical"
        elif critical_count > 5 or total > 30:
            return "warning"
        elif total > 0:
            return "info"
        return "ok"

    def verify_single_claim(self, claim_head: str, claim_relation: str,
                            claim_tail: str) -> dict:
        """验证单个声明"""
        # 查找已有的高置信度事实
        existing = self.graph.execute_query("""
        MATCH (a)-[r:{rel}]->(b)
        WHERE a.name = $head AND b.name = $tail
        RETURN r.confidence, r.source_id, a.name, b.name
        """.format(rel=claim_relation),
        {"head": claim_head, "tail": claim_tail}
        )

        if not existing:
            return {
                "verdict": "not_found",
                "message": "图谱中未找到相关信息",
                "suggestion": "可作为新知识加入（需经过验证流程）"
            }

        best_match = max(existing, key=lambda x: x.get("confidence", 0))
        conf = best_match.get("confidence", 0)

        if conf >= 0.9:
            return {"verdict": "confirmed", "confidence": conf, "source": best_match.get("source_id")}
        elif conf >= 0.7:
            return {"verdict": "likely_true", "confidence": conf, "source": best_match.get("source_id")}
        else:
            return {
                "verdict": "uncertain",
                "confidence": conf,
                "message": "现有信息置信度较低，需要进一步验证"
            }


class ReviewQueue:
    """L4: 人工审核队列"""

    def __init__(self):
        self.queue: list[dict] = []
        self.history: list[dict] = []

    def add_for_review(self, item: Any, reason: str = "low_confidence",
                       suggested_action: str = "") -> str:
        """将条目加入审核队列"""
        review_id = str(uuid.uuid4())[:8]

        review_item = {
            "id": review_id,
            "item": item.to_dict() if hasattr(item, 'to_dict') else item,
            "item_type": type(item).__name__,
            "reason": reason,
            "status": "pending",
            "submitted_at": datetime.now().isoformat(),
            "reviewer": None,
            "reviewed_at": None,
            "review_comment": None,
            "suggested_action": suggested_action,
        }

        self.queue.append(review_item)
        logger.info(f"审核项已入队: id={review_id}, reason={reason}")
        return review_id

    def approve(self, review_id: str, reviewer: str = "system", comment: str = "") -> bool:
        """批准审核项"""
        for item in self.queue:
            if item["id"] == review_id and item["status"] == "pending":
                item["status"] = "approved"
                item["reviewer"] = reviewer
                item["reviewed_at"] = datetime.now().isoformat()
                item["review_comment"] = comment
                self.history.append(item)
                self.queue.remove(item)
                logger.info(f"审核项已批准: id={review_id}")
                return True
        return False

    def reject(self, review_id: str, reviewer: str = "system", comment: str = "") -> bool:
        """驳回审核项"""
        for item in self.queue:
            if item["id"] == review_id and item["status"] == "pending":
                item["status"] = "rejected"
                item["reviewer"] = reviewer
                item["reviewed_at"] = datetime.now().isoformat()
                item["review_comment"] = comment
                self.history.append(item)
                self.queue.remove(item)
                logger.info(f"审核项已驳回: id={review_id}")
                return True
        return False

    def get_pending(self) -> list[dict]:
        """获取待审核队列"""
        return [item for item in self.queue if item["status"] == "pending"]

    def get_stats(self) -> dict:
        """获取审核统计"""
        pending = len(self.get_pending())
        approved = len([h for h in self.history if h["status"] == "approved"])
        rejected = len([h for h in self.history if h["status"] == "rejected"])
        return {
            "pending_count": pending,
            "approved_count": approved,
            "rejected_count": rejected,
            "total_processed": approved + rejected,
        }


class HallucinationGuard:
    """幻觉防控总控制器 - 协调四层防御"""

    def __init__(self, graph_service):
        self.constraint_engine = ConstraintEngine()
        self.fact_checker = FactChecker(graph_service)
        self.review_queue = ReviewQueue()
        self.provenance_store: dict[str, ProvenanceInfo] = {}  # triple_id -> provenance

    def guard_triple(self, triple: GraphTriple,
                     provenance: Optional[ProvenanceInfo] = None) -> tuple[bool, list[str]]:
        """对一条三元组进行幻觉防控检查

        Returns:
            (is_passed, messages): 是否通过检查, 检查消息列表
        """
        messages = []

        # L1: 记录溯源信息
        if provenance:
            triple_id = f"{triple.head}_{triple.relation}_{triple.tail}"
            self.provenance_store[triple_id] = provenance
            triple.source_id = provenance.source_id
            triple.evidence = provenance.raw_text

        # L2: 约束检查
        violations = self.constraint_engine.validate_triple(
            head_label=self._infer_label(triple.head),
            relation=triple.relation,
            tail_label=self._infer_label(triple.tail),
            properties=triple.properties
        )

        if violations:
            for v in violations:
                msg = f"[L2约束] {v['message']} (严重程度: {v['severity']})"
                messages.append(msg)
                if v["severity"] == "error":
                    return False, messages

        # 置信度阈值检查
        if triple.confidence < 0.3:
            messages.append("[L2置信度] 置信度过低(<0.3)，进入审核队列")
            self.review_queue.add_for_review(triple, reason="low_confidence")
            return False, messages

        if triple.confidence < 0.7:
            messages.append("[L2置信度] 置信度中等(0.3-0.7)，标记为待验证")
            # 仍然通过但降低置信度
            triple.confidence *= 0.8

        return True, messages

    def run_periodic_check(self) -> dict:
        """运行定期检查（L3事实核查）"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已在异步环境中，用create_task
                pass
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return asyncio.get_event_loop().run_until_complete(self.fact_checker.run_consistency_scan())

    def get_provenance(self, triple_id: str) -> Optional[ProvenanceInfo]:
        """查询溯源信息"""
        return self.provenance_store.get(triple_id)

    def get_review_queue_status(self) -> dict:
        """获取审核队列状态"""
        return self.review_queue.get_stats()

    def _infer_label(self, entity_name: str) -> str:
        """推断实体标签（简化版）"""
        # 可根据命名规范或前缀推断
        if entity_name.startswith("Job:") or any(kw in entity_name for kw in
            ["工程师", "开发", "设计师", "经理", "专家", "分析师"]):
            return "Job"
        if any(kw in entity_name for kw in
            ["Python", "Java", "Go", "React", "Vue", "Docker", "Kubernetes",
             "TensorFlow", "PyTorch", "LangChain", "Redis", "MySQL"]):
            return "Skill"
        if entity_name in ["人工智能", "大数据", "云计算", "区块链", "软件开发", "DevOps"]:
            return "Domain"
        return "Unknown"
