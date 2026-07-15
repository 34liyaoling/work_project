"""技术趋势感知服务

包含 4 个子模块:
- keyword_extractor: 行业报告/政策文件技术趋势关键词提取
- jd_correlator: 技术趋势与招聘 JD 关联分析
- signal_introducer: 前瞻性信号引入
- predictor: 新兴技能需求预测
"""
from app.services.trend.keyword_extractor import KeywordExtractor, get_keyword_extractor
from app.services.trend.jd_correlator import JDCorrelator, get_jd_correlator
from app.services.trend.signal_introducer import SignalIntroducer, get_signal_introducer
from app.services.trend.predictor import SkillPredictor, get_skill_predictor


__all__ = [
    "KeywordExtractor",
    "JDCorrelator",
    "SignalIntroducer",
    "SkillPredictor",
    "get_keyword_extractor",
    "get_jd_correlator",
    "get_signal_introducer",
    "get_skill_predictor",
]
