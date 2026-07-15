"""按领域分库（Domain Sharding）— 性能优化

将庞大的 Neo4j 节点按 category 拆分为多个"逻辑分片"，每个分片在 MySQL
中以 partition 标签的形式记录，查询时按 partition_id 路由，避免单次
全图扫描。

实现策略（mock 友好）:
- DomainSplitter.assign(role)  → 根据 category 决定 partition_id
- DomainSplitter.route_query(query)  → 改写为带 partition 过滤
- DomainSplitter.distribution()  → 统计各分片规模
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from app.core.logger import log


# 领域 → partition_id 映射
DEFAULT_PARTITION_MAP: Dict[str, str] = {
    "AI工程师": "p_ai",
    "算法工程师": "p_ai",
    "数据科学": "p_data",
    "数据工程": "p_data",
    "数据分析": "p_data",
    "后端开发": "p_backend",
    "前端开发": "p_frontend",
    "运维": "p_ops",
    "DevOps": "p_ops",
    "测试开发": "p_qa",
    "产品经理": "p_product",
    "设计师": "p_design",
    "嵌入式": "p_embedded",
    "芯片": "p_chip",
    "运营": "p_ops",
    "市场": "p_ops",
    "HR": "p_ops",
    "其它": "p_misc",
}


class DomainSplitter:
    """按领域分库器"""

    def __init__(self, partition_map: Optional[Dict[str, str]] = None):
        self.partition_map = partition_map or dict(DEFAULT_PARTITION_MAP)

    def assign(self, category: str) -> str:
        """根据 category 决定 partition_id"""
        return self.partition_map.get(category, self.partition_map.get("其它", "p_misc"))

    def partition_role(self, role: Dict[str, Any]) -> str:
        return self.assign(role.get("category", "其它"))

    def distribute(self, roles: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        """统计各 partition 的规模"""
        counter: Counter = Counter()
        for r in roles:
            counter[self.partition_role(r)] += 1
        return dict(counter)

    def route_query(self, cypher: str, partition_ids: Sequence[str]) -> Dict[str, Any]:
        """模拟查询路由：在真实部署中会连接对应分库实例

        :return: {"partition_ids":[...], "rewritten": True, "original": cypher}
        """
        return {
            "partition_ids": list(partition_ids),
            "rewritten": True,
            "original": cypher,
            "note": "真实部署下会执行分片并行查询并合并结果",
        }

    def split_by_category(
        self,
        roles: Sequence[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """将岗位按 partition 分组"""
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in roles:
            pid = self.partition_role(r)
            groups.setdefault(pid, []).append(r)
        return groups


_singleton: Optional[DomainSplitter] = None


def get_domain_splitter() -> DomainSplitter:
    global _singleton
    if _singleton is None:
        _singleton = DomainSplitter()
    return _singleton
