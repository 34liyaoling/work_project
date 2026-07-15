"""所有新模块的快速验证测试

运行方法: cd d:/work/competency-graph/backend && python -m pytest tests/test_new_modules.py -v
或直接:   cd d:/work/competency-graph/backend && python tests/test_new_modules.py
"""
import asyncio
import os
import sys
import unittest

# 加入项目根
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class TestCrawlerSubpackage(unittest.TestCase):
    """Task 2: 爬虫子包验证"""

    def test_imports(self):
        from app.services.crawler import (
            BaseCrawler,
            JDItem,
            BossSpider,
            ZhilianSpider,
            LiepinSpider,
            PlaywrightCrawler,
            EnterpriseSpider,  # 向后兼容别名
            IndustryReportSpider,
            PolicySpider,
            OnetSpider,
            ProxyPool,
            HTTPClient,
            CrawlPipeline,
            PipelineContext,
            SPIDER_REGISTRY,
            get_spider,
            crawl_all,
        )
        self.assertTrue(BaseCrawler)
        self.assertTrue(issubclass(BossSpider, BaseCrawler))
        self.assertTrue(issubclass(EnterpriseSpider, PlaywrightCrawler))

    def test_jditem_creation(self):
        from app.services.crawler import JDItem
        item = JDItem(
            jd_id="test-001",
            source="test",
            title="测试岗位",
            company="ACME",
            raw_text="<p>这是 HTML 文本</p>",
        )
        self.assertEqual(item.jd_id, "test-001")
        self.assertIn("HTML", item.raw_text)

    def test_proxy_pool(self):
        from app.services.crawler import ProxyPool
        p = ProxyPool(proxies=["http://a:8080", "http://b:8080"])
        self.assertEqual(p.size(), 2)
        self.assertTrue(p.get() is not None)

    def test_get_spider(self):
        from app.services.crawler import get_spider, BossSpider
        spider = get_spider("boss", use_mock=True)
        self.assertIsInstance(spider, BossSpider)

    def test_get_unknown_spider(self):
        from app.services.crawler import get_spider
        with self.assertRaises(ValueError):
            get_spider("not_exist")

    def test_crawl_mock(self):
        from app.services.crawler import BossSpider
        spider = BossSpider(use_mock=True)
        items = asyncio.run(spider.crawl("Python", pages=2))
        self.assertGreater(len(items), 0)
        self.assertTrue(all(it.source == "boss" for it in items))


class TestCleaningSubpackage(unittest.TestCase):
    """Task 3: 清洗子包验证"""

    def test_imports(self):
        from app.services.cleaning import (
            TextPreprocessor,
            SimHashDeduplicator,
            simhash,
            SkillNormalizer,
            CrossValidator,
            CredibilityScorer,
            OnetVerifier,
            CleaningPipeline,
            CleanedRecord,
        )
        self.assertTrue(TextPreprocessor)
        self.assertTrue(SimHashDeduplicator)

    def test_preprocessor(self):
        from app.services.cleaning import TextPreprocessor
        pp = TextPreprocessor()
        out = pp.process("<p>Hello <b>World</b>!   </p>")
        self.assertNotIn("<p>", out.text)
        self.assertGreater(out.removed_html, 0)

    def test_simhash(self):
        from app.services.cleaning import simhash, hamming_distance
        a = simhash("Python Java Go Rust")
        b = simhash("Python Java Go Rust")  # 相同
        c = simhash("完全不同的中文文本")
        self.assertEqual(hamming_distance(a, b), 0)
        self.assertGreater(hamming_distance(a, c), 10)

    def test_skill_normalizer(self):
        from app.services.cleaning import SkillNormalizer, normalize_skill
        std = normalize_skill("ML")
        self.assertIn(std, {"机器学习", "ML"})  # 可能原样保留或标准化
        std2 = normalize_skill("py")
        self.assertEqual(std2, "Python")

    def test_credibility_scorer(self):
        from app.services.cleaning import CredibilityScorer
        cs = CredibilityScorer()
        item = {
            "source": "boss",
            "title": "AI工程师",
            "company": "字节",
            "category": "AI",
            "level": "高级",
            "location": "北京",
            "salary_range": "30K-50K",
            "raw_text": " " * 500,
            "skills": ["Python"],
            "published_at": "2026-07-01 10:00:00",
        }
        d = cs.score(item)
        self.assertGreater(d.final_score, 0.5)
        self.assertLess(d.final_score, 1.0)

    def test_onet_verifier(self):
        from app.services.cleaning import OnetVerifier
        v = OnetVerifier()
        r = v.verify_skills(["Python", "PyTorch", "BlaBlaFakeSkill"])
        self.assertIn("Python", r.verified)
        self.assertIn("PyTorch", r.verified)
        self.assertIn("BlaBlaFakeSkill", r.unverified)

    def test_cleaning_pipeline(self):
        from app.services.cleaning import CleaningPipeline
        items = [
            {
                "jd_id": "t-001",
                "source": "boss",
                "title": "AI工程师",
                "company": "字节",
                "raw_text": "Python PyTorch LLM LLM" * 30,
                "skills": ["Python", "PyTorch", "ML"],
                "level": "高级",
                "category": "AI",
                "published_at": "2026-07-01 10:00:00",
            },
        ]
        cp = CleaningPipeline()
        results = cp.run(items)
        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertIn("Python", [s["skill"] for s in r.normalized_skills])


class TestLLMSubpackage(unittest.TestCase):
    """Task 4: LLM 子包验证"""

    def test_imports(self):
        from app.services.llm import (
            SparkClient,
            JDParser,
            ParsedJD,
            JSONValidator,
            TEMPLATES,
            JD_OUTPUT_SCHEMA,
            build_test_dataset,
            evaluate_parser,
        )
        self.assertTrue(SparkClient)
        self.assertTrue(JDParser)

    def test_spark_client_mock(self):
        from app.services.llm import SparkClient
        client = SparkClient(mock=True)
        msgs = [
            {"role": "system", "content": "你是助手"},
            {"role": "user", "content": "你好"},
        ]
        out = asyncio.run(client.chat(msgs))
        self.assertIsInstance(out, str)
        self.assertGreater(len(out), 0)

    def test_json_validator(self):
        from app.services.llm import JSONValidator
        from app.services.llm.prompts import JD_OUTPUT_SCHEMA
        v = JSONValidator(JD_OUTPUT_SCHEMA)
        data = {
            "job_title": "测试",
            "category": "AI工程师",
            "level": "高级",
            "core_responsibilities": ["a"],
            "required_skills": [],
            "preferred_skills": [],
            "typical_scenarios": [],
            "confidence": 0.8,
        }
        out = v.validate_data(data)
        self.assertTrue(out[0], f"校验失败: {out[1]}")
        # 缺字段
        out2 = v.validate_data({"job_title": "x"})
        self.assertFalse(out2[0])

    def test_prompts(self):
        from app.services.llm import render, get_schema
        msgs = render("jd_parse", jd_text="测试 JD 文本")
        self.assertIn("system", msgs)
        self.assertIn("user", msgs)
        s = get_schema("jd_parse")
        self.assertIn("job_title", s["required"])

    def test_jd_parser(self):
        from app.services.llm import JDParser
        parser = JDParser()
        result = asyncio.run(parser.parse(
            "AI工程师 - 字节跳动\n\n要求：\n1. 精通 Python、PyTorch\n2. 熟悉 LLM 应用"
        ))
        self.assertGreater(len(result.job_title), 0)
        self.assertEqual(result.parser_version, "1.0.0")

    def test_test_dataset(self):
        from app.services.llm import build_test_dataset
        cases = build_test_dataset(10)
        self.assertEqual(len(cases), 10)
        # 验证至少有 AI / 后端 / 前端 等类别
        cats = {c.expected_category for c in cases}
        self.assertGreater(len(cats), 3)

    def test_evaluate_parser(self):
        from app.services.llm import JDParser, build_test_dataset, evaluate_parser
        parser = JDParser()
        cases = build_test_dataset(5)
        report = evaluate_parser(parser, cases)
        self.assertEqual(report.total, 5)
        # 至少有 1 条成功解析
        self.assertGreater(report.parsed_ok, 0)


if __name__ == "__main__":
    # 直接运行
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
