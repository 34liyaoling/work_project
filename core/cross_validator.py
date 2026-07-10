"""多源交叉验证引擎 (MSVE) - 解决数据噪音与时滞问题"""

import logging
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Optional
from models.job_model import JobPostRaw, JobPostSource

logger = logging.getLogger(__name__)


class AgreementLevel(str, Enum):
    """一致性级别"""
    THREE_SOURCE_AGREE = "three_source_agree"     # 三源一致
    TWO_SOURCE_AGREE = "two_source_agree"          # 两源一致
    SINGLE_SOURCE = "single_source"                # 单源
    CONFLICT = "conflict"                          # 冲突


class CrossValidator:
    """多源数据交叉验证引擎

    核心机制：
    1. 每个数据源分配动态置信度权重
    2. 决策矩阵：3源一致(0.95) / 2源一致(0.75) / 冲突触发LLM仲裁
    3. 数据新鲜度评分机制解决时滞问题
    """

    # 数据源基准置信度
    SOURCE_BASE_CONFIDENCE = {
        JobPostSource.SAMPLE: 1.0,
        JobPostSource.MANUAL: 0.95,
        JobPostSource.REPORT: 0.90,
        JobPostSource.GITHUB: 0.75,
        JobPostSource.BOSS_ZHIPIN: 0.80,
        JobPostSource.LAGOU: 0.78,
        JobPostSource.LIEPIN: 0.76,
        JobPostSource.ZHAOPIN: 0.74,
    }

    # 一致性对应的置信度映射
    AGREEMENT_CONFIDENCE = {
        AgreementLevel.THREE_SOURCE_AGREE: 0.95,
        AgreementLevel.TWO_SOURCE_AGREE: 0.75,
        AgreementLevel.SINGLE_SOURCE: 0.50,
        AgreementLevel.CONFLICT: 0.25,
    }

    def __init__(self):
        # 按岗位标题聚类的数据缓存
        self._job_clusters: dict[str, list[JobPostRaw]] = defaultdict(list)
        # 数据源动态调整后的置信度
        self._source_dynamic_confidence: dict[str, float] = dict(self.SOURCE_BASE_CONFIDENCE)
        # 验证历史记录
        self._validation_history: list[dict] = []

    def add_record(self, record: JobPostRaw):
        """添加一条待验证记录"""
        key = self._cluster_key(record)
        self._job_clusters[key].append(record)

    def add_batch(self, records: list[JobPostRaw]):
        """批量添加记录"""
        for record in records:
            self.add_record(record)

    def validate_job(self, job_title: str) -> dict:
        """验证某个岗位的所有数据"""
        key = job_title.lower().strip()
        records = self._job_clusters.get(key, [])

        if not records:
            return {"valid": False, "reason": "无数据"}

        result = {
            "job_title": job_title,
            "source_count": len(set(r.source for r in records)),
            "total_records": len(records),
            "agreement_level": None,
            "validated_data": {},
            "confidence": 0.0,
            "sources_used": [],
            "conflicts": [],
            "warnings": [],
        }

        # 1. 分析各源数据的一致性
        agreement = self._analyze_agreement(records)
        result["agreement_level"] = agreement

        # 2. 计算综合置信度
        base_conf = self.AGREEMENT_CONFIDENCE.get(agreement, 0.5)
        freshness_factor = self._compute_freshness_factor(records)
        source_quality_factor = self._compute_source_quality_factor(records)

        final_confidence = base_conf * freshness_factor * source_quality_factor
        result["confidence"] = round(min(final_confidence, 1.0), 3)

        # 3. 融合多源数据
        validated = self._fuse_multi_source_data(records)
        result["validated_data"] = validated
        result["sources_used"] = list(set(r.source.value for r in records))

        # 4. 检测冲突
        conflicts = self._detect_conflicts(records)
        result["conflicts"] = conflicts

        # 5. 生成警告
        warnings = self._generate_warnings(records, validated)
        result["warnings"] = warnings

        # 记录验证历史
        self._validation_history.append({
            "timestamp": datetime.now().isoformat(),
            "job_title": job_title,
            "confidence": result["confidence"],
            "agreement": agreement,
        })

        return result

    def validate_all(self) -> list[dict]:
        """验证所有已聚类数据"""
        results = []
        for job_title in list(self._job_clusters.keys()):
            results.append(self.validate_job(job_title))
        return sorted(results, key=lambda x: x["confidence"], reverse=True)

    def _cluster_key(self, record: JobPostRaw) -> str:
        """聚类键（归一化的岗位标题）"""
        title = (record.job_title or "").lower().strip()
        # 简单归一化：去除常见变体词
        normalize_patterns = [
            (r'\(.*?\)', ''),      # 去除括号内容
            (r'（.*?）', ''),
            (r'资深?', ''),         # 去除资历修饰
            (r'(高级|中级|初级|初级?)', ''),
            (r'\s+', ' '),          # 合并空格
        ]
        for pattern, replacement in normalize_patterns:
            title = re.sub(pattern, replacement, title)
        return title.strip()

    def _analyze_agreement(self, records: list[JobPostRaw]) -> AgreementLevel:
        """分析多源数据一致性"""
        sources = set(r.source for r in records)

        if len(sources) >= 3:
            # 检查关键属性是否一致
            skill_sets = [set(r.skills) for r in records if r.skills]
            if skill_sets:
                # 计算技能集合的交集比例
                if len(skill_sets) >= 2:
                    intersection = set.intersection(*skill_sets)
                    avg_size = sum(len(s) for s in skill_sets) / len(skill_sets)
                    if avg_size > 0 and len(intersection) / avg_size > 0.5:
                        return AgreementLevel.THREE_SOURCE_AGREE
            return AgreementLevel.TWO_SOURCE_AGREE

        elif len(sources) == 2:
            return AgreementLevel.TWO_SOURCE_AGREE

        elif len(sources) == 1:
            return AgreementLevel.SINGLE_SOURCE

        return AgreementLevel.SINGLE_SOURCE

    def _compute_freshness_factor(self, records: list[JobPostRaw]) -> float:
        """计算新鲜度因子（解决时滞问题）"""
        now = datetime.now()
        total_freshness = 0
        for r in records:
            hours_old = (now - r.timestamp).total_seconds() / 3600
            # 7天内满分，之后衰减
            recency = max(0.3, 1 - hours_old / (24 * 30))
            total_freshness += recency * r.freshness_score

        return total_freshness / len(records) if records else 0.5

    def _compute_source_quality_factor(self, records: list[JobPostRaw]) -> float:
        """计算数据源质量因子"""
        total_weight = 0
        total_confidence = 0
        for r in records:
            src_conf = self._source_dynamic_confidence.get(r.source.value, 0.7)
            weight = r.completeness_score * r.source_confidence
            total_confidence += src_conf * weight
            total_weight += weight

        return total_confidence / total_weight if total_weight > 0 else 0.7

    def _fuse_multi_source_data(self, records: list[JobPostRaw]) -> dict:
        """融合多源数据（加权融合策略）"""
        fused = {}

        # 薪资融合（加权平均）
        salaries_min = [(r.salary_min, r.source_confidence, r.freshness_score)
                        for r in records if r.salary_min]
        salaries_max = [(r.salary_max, r.source_confidence, r.freshness_score)
                        for r in records if r.salary_max]

        if salaries_min:
            weights = [c * f for _, c, f in salaries_min]
            fused["salary_min"] = self._weighted_avg([s for s, _, _ in salaries_min], weights)

        if salaries_max:
            weights = [c * f for _, c, f in salaries_max]
            fused["salary_max"] = self._weighted_avg([s for s, _, _ in salaries_max], weights)

        # 技能融合（频率+置信度加权）
        skill_freq: dict[str, float] = defaultdict(float)
        for r in records:
            for skill in (r.skills or []):
                skill_freq[skill] += r.source_confidence * r.completeness_score

        # 排序并取top skills
        sorted_skills = sorted(skill_freq.items(), key=lambda x: x[1], reverse=True)
        fused["all_skills"] = [s for s, _ in sorted_skills]
        fused["core_skills"] = [s for s, _ in sorted_skills[:15]]
        fused["skill_weights"] = dict(sorted_skills)

        # 经验要求融合
        exp_mins = [r.experience_min for r in records if r.experience_min is not None]
        exp_maxs = [r.experience_max for r in records if r.experience_max is not None]
        if exp_mins:
            fused["experience_min"] = min(exp_mins)
        if exp_maxs:
            fused["experience_max"] = max(exp_maxs)

        # 地点融合（取最常见的）
        locations = [r.location for r in records if r.location]
        if locations:
            loc_freq = defaultdict(int)
            for loc in locations:
                loc_freq[loc] += 1
            fused["primary_location"] = max(loc_freq.keys(), key=lambda k: loc_freq[k])
            fused["all_locations"] = list(set(locations))

        # 公司样本
        companies = [r.company_name for r in records if r.company_name]
        fused["sample_companies"] = list(set(companies))[:10]

        # 来源计数
        source_counts = defaultdict(int)
        for r in records:
            source_counts[r.source.value] += 1
        fused["source_counts"] = dict(source_counts)

        # 更新时间
        latest = max((r.timestamp for r in records), default=datetime.now())
        fused["latest_update"] = latest.isoformat()

        return fused

    def _detect_conflicts(self, records: list[JobPostRaw]) -> list[dict]:
        """检测数据冲突"""
        conflicts = []

        # 薪资冲突：不同源薪资差异过大
        salaries = [(r.salary_min, r.salary_max, r.source.value) for r in records
                    if r.salary_min and r.salary_max]
        if len(salaries) >= 2:
            avg_salaries = [(s_min + s_max) / 2 for s_min, s_max, _ in salaries]
            if max(avg_salaries) > 0:
                ratio = max(avg_salaries) / min(avg_salaries)
                if ratio > 2.0:
                    conflicts.append({
                        "type": "salary_conflict",
                        "severity": "high",
                        "details": f"薪资差异达{ratio:.1f}倍",
                        "values": [{"source": s, "avg": (mn+mx)/2} for mn, mx, s in salaries]
                    })

        # 经验要求冲突
        experiences = [(r.experience_min, r.experience_max, r.source.value)
                      for r in records if r.experience_min is not None]
        if len(experiences) >= 2:
            min_exps = [e[0] for e in experiences]
            if max(min_exps) > 0 and max(min_exps) / max(min(min_exps), 1) > 3:
                conflicts.append({
                    "type": "experience_conflict",
                    "severity": "medium",
                    "details": "经验要求差异较大",
                    "values": experiences
                })

        return conflicts

    def _generate_warnings(self, records: list[JobPostRaw], validated: dict) -> list[str]:
        """生成警告信息"""
        warnings = []

        # 数据量不足
        if len(records) < 3:
            warnings.append(f"数据量较少({len(records)}条)，验证结果可能不够稳定")

        # 完整度偏低
        avg_completeness = sum(r.completeness_score for r in records) / len(records)
        if avg_completeness < 0.5:
            warnings.append(f"数据完整度较低({avg_completeness:.0%})，部分关键字段缺失")

        # 新鲜度偏低
        avg_freshness = sum(r.freshness_score for r in records) / len(records)
        if avg_freshness < 0.5:
            warnings.append(f"数据较陈旧({avg_freshness:.0%})，可能存在时滞")

        # 单一来源风险
        sources = set(r.source for r in records)
        if len(sources) == 1:
            warnings.append(f"仅来自单一数据源({list(sources)[0].value})，建议补充其他来源")

        return warnings

    def _weighted_avg(self, values: list, weights: list) -> float:
        """加权平均"""
        if not values:
            return 0
        total_weight = sum(weights)
        if total_weight == 0:
            return sum(values) / len(values)
        return sum(v * w for v, w in zip(values, weights)) / total_weight

    def adjust_source_confidence(self, source: str, delta: float):
        """动态调整某数据源的置信度"""
        current = self._source_dynamic_confidence.get(source, 0.7)
        new_val = max(0.1, min(1.0, current + delta))
        self._source_dynamic_confidence[source] = new_val
        logger.info(f"数据源[{source}]置信度调整: {current:.2f} → {new_val:.2f}")

    def get_validation_summary(self) -> dict:
        """获取验证摘要"""
        return {
            "total_clusters": len(self._job_clusters),
            "total_records": sum(len(v) for v in self._job_clusters.values()),
            "source_confidences": self._source_dynamic_confidence,
            "validation_count": len(self._validation_history),
        }


import re
