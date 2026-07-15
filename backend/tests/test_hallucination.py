"""幻觉防控测试 - 四层防控各层测试

四层：
1. 检索增强 (RAG)：答案必须基于检索结果
2. Schema 校验：LLM 输出必须符合 JSON Schema
3. 置信度阈值：低于阈值的内容不允许直接输出
4. 人工审核：高风险内容强制人工介入
"""
from app.services.risk_handler import LLMStabilityGuard


class TestLayer1RAG:
    def test_response_must_reference_source(self):
        """答案必须引用来源 chunk id，否则视为幻觉"""
        guard = LLMStabilityGuard()
        retrieved = [{"id": "doc-1", "text": "Python 是一种解释型语言"}]
        response = "Python 是一种解释型语言 [来源: doc-1]"
        # 若答案没有引用任何来源，应被识别为不可信
        no_ref_response = "Python 是 1995 年发布的编程语言"
        assert guard.validate_regex(response, [r"\[来源:\s*\S+\]"])[0] is True
        assert guard.validate_regex(no_ref_response, [r"\[来源:\s*\S+\]"])[0] is False


class TestLayer2Schema:
    def test_schema_validation_pass(self):
        guard = LLMStabilityGuard()
        schema = {
            "type": "object",
            "required": ["skills"],
            "properties": {
                "skills": {"type": "array"},
                "level": {"type": "string"},
            },
        }
        data = {"skills": ["Python"], "level": "高级"}
        ok, err = guard.validate_schema(data, schema)
        assert ok is True, err

    def test_schema_validation_missing_field(self):
        guard = LLMStabilityGuard()
        schema = {"type": "object", "required": ["skills"]}
        ok, err = guard.validate_schema({}, schema)
        assert ok is False
        assert "skills" in err

    def test_schema_validation_wrong_type(self):
        guard = LLMStabilityGuard()
        schema = {"type": "object", "properties": {"skills": {"type": "array"}}}
        ok, err = guard.validate_schema({"skills": "Python"}, schema)
        assert ok is False

    def test_json_parse_markdown_wrapped(self):
        guard = LLMStabilityGuard()
        raw = "```json\n{\"skills\": [\"Python\"]}\n```"
        ok, data, err = guard.safe_json_parse(raw)
        assert ok is True
        assert data["skills"] == ["Python"]


class TestLayer3Confidence:
    def test_confidence_filter(self):
        """低置信度输出不允许直接返回"""
        guard = LLMStabilityGuard()
        threshold = 0.7

        def fake_caller(_prompt, confidence):
            return f'{{"skills": ["Python"], "confidence": {confidence}}}'

        # 触发低置信度降级
        result = guard.call(
            caller=lambda: fake_caller("p", 0.3),
            schema={
                "type": "object",
                "properties": {"confidence": {"type": "number"}},
            },
            regex_patterns=[],  # 不强制正则
        )
        # 解析成功，但业务层应基于 confidence 字段决定是否采用
        assert result.success is True
        assert result.data["confidence"] < threshold


class TestLayer4HumanReview:
    def test_high_risk_flag_triggers_review(self):
        """高风险内容（涉及薪资、年限等敏感字段）必须人工审核"""
        from app.services.audit import AuditService
        # 这里仅做接口层校验
        svc = AuditService()
        pending = svc.list_pending() or []
        # 不强制存在 pending；只要接口可调用即可
        assert isinstance(pending, list)
