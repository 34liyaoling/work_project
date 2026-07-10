"""幻觉防控测试 - ConstraintEngine、ProvenanceInfo、ReviewQueue（mock模式）"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from models.graph_nodes import GraphTriple
from core.hallucination_guard import (
    ProvenanceInfo, ConstraintEngine, FactChecker,
    ReviewQueue, HallucinationGuard,
)


class TestProvenanceInfo:
    """ProvenanceInfo 创建测试"""

    def test_create(self):
        """测试 ProvenanceInfo 创建"""
        info = ProvenanceInfo(
            source_id="src_001",
            source_type="resume",
            record_id="rec_001",
            raw_text="精通Python和机器学习",
            method="extraction",
        )
        assert info.source_id == "src_001"
        assert info.source_type == "resume"
        assert info.raw_text == "精通Python和机器学习"
        assert isinstance(info.timestamp, datetime)

    def test_raw_text_truncation(self):
        """测试原始文本截断"""
        long_text = "a" * 1000
        info = ProvenanceInfo(
            source_id="src_001",
            source_type="test",
            record_id="rec_001",
            raw_text=long_text,
        )
        assert len(info.raw_text) == 500

    def test_to_dict(self):
        """测试 to_dict 方法"""
        info = ProvenanceInfo(
            source_id="src_001",
            source_type="resume",
            record_id="rec_001",
            raw_text="Python",
            method="extraction",
        )
        d = info.to_dict()
        assert d["source_id"] == "src_001"
        assert d["source_type"] == "resume"
        assert "timestamp" in d

    def test_default_method(self):
        """测试默认 method"""
        info = ProvenanceInfo(
            source_id="src_001",
            source_type="test",
            record_id="rec_001",
        )
        assert info.method == "unknown"


class TestConstraintEngine:
    """约束引擎测试"""

    @pytest.fixture
    def engine(self):
        return ConstraintEngine()

    def test_type_constraint_valid(self, engine):
        """测试有效类型约束"""
        violations = engine._check_type_constraint("Skill", "similar_to", "Skill")
        assert len(violations) == 0

    def test_type_constraint_invalid(self, engine):
        """测试无效类型约束"""
        violations = engine._check_type_constraint("Skill", "similar_to", "Job")
        assert len(violations) == 1
        assert violations[0]["type"] == "type_violation"

    def test_value_constraint_difficulty(self, engine):
        """测试数值约束 - difficulty"""
        violations = engine._check_value_constraints({"difficulty": 5})
        assert len(violations) == 0

        violations = engine._check_value_constraints({"difficulty": 15})
        assert len(violations) == 1
        assert violations[0]["type"] == "value_out_of_range"

    def test_value_constraint_confidence(self, engine):
        """测试数值约束 - confidence"""
        violations = engine._check_value_constraints({"confidence": 0.5})
        assert len(violations) == 0

        violations = engine._check_value_constraints({"confidence": 1.5})
        assert len(violations) == 1

    def test_value_constraint_trend_score(self, engine):
        """测试数值约束 - trend_score"""
        violations = engine._check_value_constraints({"trend_score": 0.0})
        assert len(violations) == 0

        violations = engine._check_value_constraints({"trend_score": -2.0})
        assert len(violations) == 1

    def test_value_constraint_version(self, engine):
        """测试数值约束 - version 格式校验"""
        violations = engine._check_value_constraints({"version": "1.0"})
        version_violations = [v for v in violations if v["type"] == "format_error"]
        assert len(version_violations) <= 1

    def test_value_constraint_type_error(self, engine):
        """测试数值约束 - 类型错误"""
        violations = engine._check_value_constraints({"difficulty": "high"})
        assert len(violations) >= 1

    def test_validate_triple_no_violations(self, engine):
        """测试完整验证 - 无违规"""
        violations = engine.validate_triple("Skill", "similar_to", "Skill")
        assert len(violations) == 0

    def test_validate_triple_with_properties(self, engine):
        """测试带属性的完整验证"""
        violations = engine.validate_triple(
            "Skill", "similar_to", "Skill",
            properties={"difficulty": 8, "confidence": 0.9},
        )
        assert len(violations) == 0

    def test_validate_triple_type_violation(self, engine):
        """测试类型违规"""
        violations = engine.validate_triple(
            "Skill", "similar_to", "Job",
        )
        assert len(violations) == 1

    def test_validate_triple_value_violation(self, engine):
        """测试数值违规"""
        violations = engine.validate_triple(
            "Skill", "similar_to", "Skill",
            properties={"difficulty": 20},
        )
        assert len(violations) == 1

    def test_mutex_requires_prefers(self, engine):
        """测试互斥规则 - 同一技能不能同时required和prefers"""
        existing = [
            GraphTriple(head="Job:AI", relation="requires", tail="Skill:Python"),
        ]
        new = GraphTriple(head="Job:AI", relation="prefers", tail="Skill:Python")

        violations = engine.check_mutex_rules(existing, new)
        assert len(violations) == 1
        assert violations[0]["type"] == "mutex_violation"

    def test_mutex_no_violation(self, engine):
        """测试互斥规则 - 不同技能无冲突"""
        existing = [
            GraphTriple(head="Job:AI", relation="requires", tail="Skill:Python"),
        ]
        new = GraphTriple(head="Job:AI", relation="prefers", tail="Skill:Java")

        violations = engine.check_mutex_rules(existing, new)
        assert len(violations) == 0

    def test_valid_relation_types(self, engine):
        """测试所有有效关系类型"""
        valid_combos = [
            ("Skill", "similar_to", "Skill"),
            ("Job", "requires", "Skill"),
            ("Job", "prefers", "Skill"),
            ("Skill", "belongs_to", "Domain"),
            ("Skill", "evolves_to", "Skill"),
            ("Person", "has_skill", "Skill"),
            ("Person", "applied_for", "Job"),
        ]
        for h, r, t in valid_combos:
            violations = engine.validate_triple(h, r, t)
            assert len(violations) == 0, f"组合({h}, {r}, {t})不应有违规"


class TestReviewQueue:
    """审核队列测试"""

    @pytest.fixture
    def queue(self):
        return ReviewQueue()

    def test_add_for_review(self, queue):
        """测试添加审核项"""
        item = GraphTriple(head="Python", relation="similar_to", tail="Java")
        review_id = queue.add_for_review(item, reason="low_confidence")
        assert review_id is not None
        assert len(review_id) == 8
        assert len(queue.get_pending()) == 1

    def test_approve(self, queue):
        """测试批准"""
        item = GraphTriple(head="A", relation="r", tail="B")
        review_id = queue.add_for_review(item)

        result = queue.approve(review_id, reviewer="admin", comment="ok")
        assert result is True
        assert len(queue.get_pending()) == 0

    def test_approve_nonexistent(self, queue):
        """测试批准不存在的项"""
        result = queue.approve("nonexistent")
        assert result is False

    def test_reject(self, queue):
        """测试驳回"""
        item = GraphTriple(head="A", relation="r", tail="B")
        review_id = queue.add_for_review(item)

        result = queue.reject(review_id, reviewer="admin", comment="invalid")
        assert result is True
        assert len(queue.get_pending()) == 0

    def test_get_stats(self, queue):
        """测试审核统计"""
        item = GraphTriple(head="A", relation="r", tail="B")
        queue.add_for_review(item)

        stats = queue.get_stats()
        assert stats["pending_count"] == 1
        assert stats["total_processed"] == 0


class TestHallucinationGuard:
    """幻觉防控总控制器测试"""

    @pytest.fixture
    def guard(self):
        mock_graph = MagicMock()
        return HallucinationGuard(mock_graph)

    def test_guard_triple_passed(self, guard):
        """测试三元组通过检查"""
        triple = GraphTriple(
            head="Python",
            relation="similar_to",
            tail="Java",
            confidence=0.9,
        )
        passed, messages = guard.guard_triple(triple)
        assert passed is True

    def test_guard_triple_with_provenance(self, guard):
        """测试带溯源信息的三元组"""
        triple = GraphTriple(
            head="Python",
            relation="similar_to",
            tail="Java",
            confidence=0.9,
        )
        provenance = ProvenanceInfo(
            source_id="src_001",
            source_type="resume",
            record_id="rec_001",
        )
        passed, messages = guard.guard_triple(triple, provenance)
        assert passed is True
        assert triple.source_id == "src_001"

    def test_guard_type_violation(self, guard):
        """测试类型违规导致不通过"""
        triple = GraphTriple(
            head="Python",
            relation="similar_to",
            tail="Job:AI",
            confidence=0.9,
        )
        passed, messages = guard.guard_triple(triple)
        assert passed is False
        assert any("[L2约束]" in m for m in messages)

    def test_low_confidence_enters_review(self, guard):
        """测试低置信度进入审核队列"""
        triple = GraphTriple(
            head="Python",
            relation="similar_to",
            tail="Java",
            confidence=0.2,
        )
        passed, messages = guard.guard_triple(triple)
        assert passed is False
        assert any("置信度过低" in m for m in messages)
        assert guard.review_queue.get_stats()["pending_count"] == 1

    def test_medium_confidence_marked(self, guard):
        """测试中等置信度标记"""
        triple = GraphTriple(
            head="Python",
            relation="similar_to",
            tail="Java",
            confidence=0.5,
        )
        passed, messages = guard.guard_triple(triple)
        assert passed is True
        original_conf = triple.confidence
        assert original_conf < 0.5

    def test_get_provenance(self, guard):
        """测试查询溯源信息"""
        triple = GraphTriple(
            head="Python", relation="similar_to", tail="Java", confidence=0.9,
        )
        provenance = ProvenanceInfo("src_001", "resume", "rec_001")
        guard.guard_triple(triple, provenance)

        retrieved = guard.get_provenance("Python_similar_to_Java")
        assert retrieved is not None
        assert retrieved.source_id == "src_001"

    def test_get_provenance_not_found(self, guard):
        """测试查询不存在的溯源信息"""
        retrieved = guard.get_provenance("nonexistent")
        assert retrieved is None

    def test_get_review_queue_status(self, guard):
        """测试获取审核队列状态"""
        status = guard.get_review_queue_status()
        assert "pending_count" in status
        assert "approved_count" in status

    def test_infer_label_job(self, guard):
        """测试推断Job标签"""
        label = guard._infer_label("Python工程师")
        assert label == "Job"

    def test_infer_label_skill(self, guard):
        """测试推断Skill标签"""
        label = guard._infer_label("Python")
        assert label == "Skill"

    def test_infer_label_domain(self, guard):
        """测试推断Domain标签"""
        label = guard._infer_label("人工智能")
        assert label == "Domain"
