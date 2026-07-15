"""技能组合聚类分析

通过将 JD 文本中的技能表示为 one-hot / TF-IDF 风格向量，
使用 KMeans（指定簇数）与 DBSCAN（基于密度）两种算法发现
非标准化的"技能组合簇"，进而识别新兴岗位。
"""
from __future__ import annotations

import hashlib
import math
from collections import Counter
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from app.core.logger import log

# sklearn / numpy 为可选依赖
try:
    import numpy as np  # type: ignore
    from sklearn.cluster import KMeans, DBSCAN  # type: ignore
    HAS_SKLEARN = True
except Exception:  # pragma: no cover
    np = None  # type: ignore
    KMeans = None  # type: ignore
    DBSCAN = None  # type: ignore
    HAS_SKLEARN = False


class ClusterAnalyzer:
    """技能组合聚类分析器

    输入: 一组 JD 的技能集合（list[list[str]]），并可附带 source/company 元数据
    输出: 簇列表，每簇含 cluster_id、size、核心技能组合、来源平台、跨公司数等
    """

    def __init__(self, k: int = 5, eps: float = 0.55, min_samples: int = 3):
        self.k = k
        self.eps = eps
        self.min_samples = min_samples

    # ----------------- 公开 API -----------------
    def cluster(
        self,
        jd_skill_sets: Sequence[Sequence[str]],
        jd_sources: Optional[Sequence[str]] = None,
        jd_companies: Optional[Sequence[str]] = None,
    ) -> List[Dict]:
        """对技能组合集合做聚类

        :param jd_skill_sets: 每个 JD 包含的技能集合（list[list[str]]）
        :param jd_sources: 每个 JD 的数据来源（如 boss/拉勾/猎聘）
        :param jd_companies: 每个 JD 的公司名
        :return: 簇列表（每项含 cluster_id/size/skills/sources/companies/score）
        """
        if not jd_skill_sets:
            return []

        # 过滤空集合
        valid_indices = [i for i, s in enumerate(jd_skill_sets) if s]
        if len(valid_indices) < max(self.min_samples, 2):
            log.warning(f"有效样本数 {len(valid_indices)} 不足，返回单簇")
            return [self._build_cluster(0, list(range(len(jd_skill_sets))), jd_skill_sets,
                                        jd_sources, jd_companies)]

        skill_sets = [list(jd_skill_sets[i]) for i in valid_indices]
        sources = [jd_sources[i] if jd_sources else "unknown" for i in valid_indices]
        companies = [jd_companies[i] if jd_companies else "unknown" for i in valid_indices]

        if HAS_SKLEARN:
            labels = self._sklearn_cluster(skill_sets)
        else:
            labels = self._fallback_cluster(skill_sets)

        return self._build_clusters(labels, skill_sets, sources, companies)

    # ----------------- 内部: sklearn 聚类 -----------------
    def _sklearn_cluster(self, skill_sets: List[List[str]]) -> List[int]:
        """基于技能 Jaccard 距离做 DBSCAN + KMeans 双路聚类合并"""
        # 1. 特征化：技能 -> 全局索引
        all_skills = sorted({s for skills in skill_sets for s in skills})
        if not all_skills:
            return [0] * len(skill_sets)
        idx_map = {s: i for i, s in enumerate(all_skills)}

        # 2. one-hot 矩阵
        vectors = np.zeros((len(skill_sets), len(all_skills)), dtype=np.float32)
        for i, skills in enumerate(skill_sets):
            for s in skills:
                if s in idx_map:
                    vectors[i, idx_map[s]] = 1.0

        # 3. KMeans（提供主簇结构）
        n_clusters = min(self.k, max(1, len(skill_sets) // max(1, self.min_samples)))
        try:
            km = KMeans(n_clusters=n_clusters, n_init=5, random_state=42)
            km_labels = km.fit_predict(vectors).tolist()
        except Exception as e:  # pragma: no cover
            log.warning(f"KMeans 失败: {e}")
            km_labels = [0] * len(skill_sets)

        # 4. DBSCAN（捕捉离群新簇）
        try:
            db = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric="cosine")
            db_labels = db.fit_predict(vectors).tolist()
        except Exception as e:  # pragma: no cover
            log.warning(f"DBSCAN 失败: {e}")
            db_labels = [-1] * len(skill_sets)

        # 5. 合并: DBSCAN 标签不为 -1 的优先（更精细的离群点识别）
        labels: List[int] = []
        max_km = max(km_labels) if km_labels else 0
        for km_lab, db_lab in zip(km_labels, db_labels):
            if db_lab != -1:
                labels.append(int(max_km + 1 + db_lab))
            else:
                labels.append(int(km_lab))
        return labels

    # ----------------- 内部: 降级聚类 -----------------
    def _fallback_cluster(self, skill_sets: List[List[str]]) -> List[int]:
        """无 sklearn 时使用贪心 Jaccard 距离做层次聚类"""
        n = len(skill_sets)
        labels = [-1] * n
        next_label = 0
        for i in range(n):
            if labels[i] != -1:
                continue
            labels[i] = next_label
            for j in range(i + 1, n):
                if labels[j] != -1:
                    continue
                if self._jaccard(skill_sets[i], skill_sets[j]) >= 1 - self.eps:
                    labels[j] = next_label
            next_label += 1
        return labels

    @staticmethod
    def _jaccard(a: Sequence[str], b: Sequence[str]) -> float:
        sa, sb = set(a), set(b)
        if not sa and not sb:
            return 0.0
        return len(sa & sb) / max(1, len(sa | sb))

    # ----------------- 内部: 构建簇描述 -----------------
    def _build_clusters(
        self,
        labels: List[int],
        skill_sets: List[List[str]],
        sources: List[str],
        companies: List[str],
    ) -> List[Dict]:
        clusters: Dict[int, List[int]] = {}
        for idx, lab in enumerate(labels):
            clusters.setdefault(int(lab), []).append(idx)

        result: List[Dict] = []
        for lab, indices in clusters.items():
            cluster = self._build_cluster(lab, indices, skill_sets, sources, companies)
            result.append(cluster)
        # 按簇大小降序
        result.sort(key=lambda x: x["size"], reverse=True)
        return result

    def _build_cluster(
        self,
        label: int,
        indices: List[int],
        skill_sets: List[List[str]],
        sources: Optional[Sequence[str]],
        companies: Optional[Sequence[str]],
    ) -> Dict:
        """聚合单簇信息"""
        member_skills: List[str] = []
        for i in indices:
            member_skills.extend(skill_sets[i])
        skill_counter = Counter(member_skills)
        # 核心技能：出现频次 > 50% 簇大小的技能
        threshold = max(1, int(len(indices) * 0.5))
        core_skills = [s for s, c in skill_counter.most_common() if c >= threshold]
        # top 技能（频次排序）
        top_skills = [s for s, _ in skill_counter.most_common(15)]

        cluster_sources = [sources[i] for i in indices] if sources else []
        cluster_companies = [companies[i] for i in indices] if companies else []

        cluster_id = f"cluster_{label}_{self._hash(str(sorted(indices)))}"
        return {
            "cluster_id": cluster_id,
            "label": int(label),
            "size": len(indices),
            "skills": top_skills,
            "core_skills": core_skills,
            "skill_freq": {s: int(c) for s, c in skill_counter.most_common()},
            "sources": sorted(set(cluster_sources)),
            "companies": sorted(set(cluster_companies)),
            "company_count": len(set(cluster_companies)),
            "sample_jd_indices": indices[:5],
        }

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:8]


_singleton: Optional[ClusterAnalyzer] = None


def get_cluster_analyzer() -> ClusterAnalyzer:
    """获取全局单例"""
    global _singleton
    if _singleton is None:
        _singleton = ClusterAnalyzer()
    return _singleton
