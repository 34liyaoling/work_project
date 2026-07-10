"""Neo4j 图谱操作服务"""

import logging
from datetime import datetime
from typing import Any, Optional
from config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class GraphService:
    """Neo4j图数据库操作封装"""

    def __init__(self):
        self._driver = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """连接到Neo4j数据库"""
        if self._connected:
            return True
        try:
            from neo4j import GraphDatabase

            uri = settings.neo4j.uri
            user = settings.neo4j.user
            password = settings.neo4j.password

            self._driver = GraphDatabase.driver(
                uri,
                auth=(user, password)
            )
            with self._driver.session() as session:
                session.run("RETURN 1")
            self._connected = True
            logger.info(f"成功连接Neo4j: {settings.neo4j.uri}")
            return True
        except Exception as e:
            logger.error(f"Neo4j连接失败: {e}")
            raise RuntimeError(f"Neo4j数据库连接失败，请检查数据库是否已启动: {e}")

    def close(self):
        """关闭连接"""
        if self._driver:
            self._driver.close()
            self._connected = False

    def _get_session(self):
        """获取会话（自动重连）"""
        if not self._connected or self._driver is None:
            self.connect()
            if not self._connected:
                raise RuntimeError("Neo4j连接失败，请检查数据库是否已启动")
        return self._driver.session()

    # ==================== 节点操作 ====================

    def create_skill_node(self, skill_data: dict) -> bool:
        """创建或更新技能节点"""
        cypher = """
        MERGE (s:Skill {name: $name})
        SET s += $props,
            s.last_updated = datetime()
        RETURN s
        """
        props = {k: v for k, v in skill_data.items() if k != 'name'}
        try:
            with self._get_session() as session:
                session.run(cypher, name=skill_data['name'], props=props)
            return True
        except Exception as e:
            logger.error(f"创建技能节点失败 [{skill_data.get('name')}]: {e}")
            return False

    def create_job_node(self, job_data: dict) -> bool:
        """创建或更新岗位节点"""
        cypher = """
        MERGE (j:Job {title: $title})
        SET j += $props,
            j.last_updated = datetime()
        RETURN j
        """
        props = {k: v for k, v in job_data.items() if k != 'title'}
        try:
            with self._get_session() as session:
                session.run(cypher, title=job_data['title'], props=props)
            return True
        except Exception as e:
            logger.error(f"创建岗位节点失败 [{job_data.get('title')}]: {e}")
            return False

    def create_domain_node(self, name: str, **kwargs) -> bool:
        """创建领域节点"""
        cypher = """
        MERGE (d:Domain {name: $name})
        SET d += $props
        RETURN d
        """
        try:
            with self._get_session() as session:
                session.run(cypher, name=name, props=kwargs)
            return True
        except Exception as e:
            logger.error(f"创建领域节点失败 [{name}]: {e}")
            return False

    def create_person_node(self, person_data: dict) -> bool:
        """创建人员节点（简历解析后）"""
        cypher = """
        MERGE (p:Person {resume_hash: $resume_hash})
        SET p += $props,
            p.created_at = datetime()
        RETURN p
        """
        try:
            with self._get_session() as session:
                session.run(cypher, resume_hash=person_data['resume_hash'],
                           props={k: v for k, v in person_data.items() if k != 'resume_hash'})
            return True
        except Exception as e:
            logger.error(f"创建人员节点失败: {e}")
            return False

    # ==================== 关系操作 ====================

    def create_requires_relation(self, job_title: str, skill_name: str,
                                  required: bool = True, confidence: float = 0.8,
                                  **kwargs) -> bool:
        """创建岗位-技能需求关系"""
        rel_type = "requires" if required else "prefers"
        cypher = f"""
        MATCH (j:Job {{title: $job_title}})
        MATCH (s:Skill {{name: $skill_name}})
        MERGE (j)-[r:{rel_type}]->(s)
        SET r.confidence = $confidence,
            r.created_at = datetime(),
            r += $props
        RETURN r
        """
        try:
            with self._get_session() as session:
                session.run(cypher, job_title=job_title, skill_name=skill_name,
                           confidence=confidence, props=kwargs)
            return True
        except Exception as e:
            logger.error(f"创建关系失败 [{job_title}-{rel_type}->{skill_name}]: {e}")
            return False

    def create_belongs_to_relation(self, skill_name: str, domain_name: str) -> bool:
        """创建技能-领域归属关系"""
        if not skill_name or not domain_name:
            return False
        cypher = """
        MATCH (s:Skill {name: $skill_name})
        MATCH (d:Domain {name: $domain_name})
        MERGE (s)-[:belongs_to]->(d)
        RETURN s, d
        """
        try:
            with self._get_session() as session:
                session.run(cypher, skill_name=skill_name, domain_name=domain_name)
            return True
        except Exception as e:
            logger.error(f"创建归属关系失败: {e}")
            return False

    def create_prerequisite_relation(self, skill_a: str, skill_b: str) -> bool:
        """创建技能先修关系 (skill_b 是 skill_a 的先修)"""
        if not skill_a or not skill_b:
            return False
        cypher = """
        MATCH (a:Skill {name: $a})
        MATCH (b:Skill {name: $b})
        MERGE (a)-[r:prerequisite_for]->(b)
        SET r.created_at = datetime()
        RETURN r
        """
        try:
            with self._get_session() as session:
                session.run(cypher, a=skill_a, b=skill_b)
            return True
        except Exception as e:
            logger.error(f"创建先修关系失败 [{skill_a} -> {skill_b}]: {e}")
            return False

    def create_synonym_relation(self, skill_a: str, skill_b: str) -> bool:
        """创建技能同义词关系"""
        if not skill_a or not skill_b:
            return False
        cypher = """
        MATCH (a:Skill {name: $a})
        MATCH (b:Skill {name: $b})
        MERGE (a)-[r:synonym_of]->(b)
        SET r.created_at = datetime()
        RETURN r
        """
        try:
            with self._get_session() as session:
                session.run(cypher, a=skill_a, b=skill_b)
            return True
        except Exception as e:
            logger.error(f"创建同义词关系失败 [{skill_a} - {skill_b}]: {e}")
            return False

    def create_similar_relation(self, skill_a: str, skill_b: str, similarity: float) -> bool:
        """创建技能相似关系"""
        cypher = """
        MATCH (a:Skill {name: $a})
        MATCH (b:Skill {name: $b})
        MERGE (a)-[r:similar_to]->(b)
        SET r.similarity = $similarity, r.updated_at = datetime()
        RETURN r
        """
        try:
            with self._get_session() as session:
                session.run(cypher, a=skill_a, b=skill_b, similarity=similarity)
            return True
        except Exception as e:
            logger.error(f"创建相似关系失败: {e}")
            return False

    def create_has_skill_relation(self, resume_hash: str, skill_name: str,
                                   level: float = 0.8) -> bool:
        """创建人员-技能拥有关系"""
        cypher = """
        MATCH (p:Person {resume_hash: $hash})
        MATCH (s:Skill {name: $skill})
        MERGE (p)-[r:has_skill]->(s)
        SET r.level = $level, r.updated_at = datetime()
        RETURN r
        """
        try:
            with self._get_session() as session:
                session.run(cypher, hash=resume_hash, skill=skill_name, level=level)
            return True
        except Exception as e:
            logger.error(f"创建has_skill关系失败: {e}")
            return False

    # ==================== 查询操作 ====================

    def get_job_required_skills(self, job_title: str, fuzzy: bool = True) -> list[dict]:
        """获取岗位所需的所有技能
        
        Args:
            job_title: 岗位名称
            fuzzy: 是否使用模糊搜索
        """
        if fuzzy:
            # 模糊搜索：查找包含关键词的岗位
            cypher = """
            MATCH (j:Job)-[r]->(s:Skill)
            WHERE j.title CONTAINS $keyword OR $keyword CONTAINS j.title
            RETURN j.title as matched_title, type(r) as relation_type, s.name as skill_name,
                   s.category, s.difficulty, s.trend_score, r.confidence
            ORDER BY CASE WHEN type(r)='requires' THEN 0 ELSE 1 END, r.confidence DESC
            """
            keyword = job_title.replace("招聘", "").replace("2026", "").replace("年", "").strip()
        else:
            # 精确搜索
            cypher = """
            MATCH (j:Job {title: $title})-[r]->(s:Skill)
            RETURN j.title as matched_title, type(r) as relation_type, s.name as skill_name,
                   s.category, s.difficulty, s.trend_score, r.confidence
            ORDER BY CASE WHEN type(r)='requires' THEN 0 ELSE 1 END, r.confidence DESC
            """
            keyword = job_title
        
        try:
            with self._get_session() as session:
                result = session.run(cypher, title=keyword, keyword=keyword)
                records = [record.data() for record in result]
                
                # 如果模糊搜索没结果，尝试模糊匹配任意关键词
                if not records and fuzzy:
                    for kw in keyword:
                        if len(kw) >= 2:
                            cypher_fuzzy = """
                            MATCH (j:Job)-[r]->(s:Skill)
                            WHERE j.title CONTAINS $kw
                            RETURN j.title as matched_title, type(r) as relation_type, s.name as skill_name,
                                   s.category, s.difficulty, s.trend_score, r.confidence
                            ORDER BY CASE WHEN type(r)='requires' THEN 0 ELSE 1 END, r.confidence DESC
                            LIMIT 20
                            """
                            result = session.run(cypher_fuzzy, kw=kw)
                            records = [record.data() for record in result]
                            if records:
                                break
                
                return records
        except Exception as e:
            logger.error(f"查询岗位技能失败: {e}")
            return []

    def get_person_skills(self, resume_hash: str) -> list[dict]:
        """获取人员的技能列表"""
        cypher = """
        MATCH (p:Person {resume_hash: $hash})-[r:has_skill]->(s:Skill)
        RETURN s.name, s.category, s.domain, s.trend_score, r.level
        ORDER BY r.level DESC
        """
        try:
            with self._get_session() as session:
                result = session.run(cypher, hash=resume_hash)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"查询人员技能失败: {e}")
            return []

    def find_similar_skills(self, skill_name: str, limit: int = 10) -> list[dict]:
        """查找相似技能"""
        cypher = """
        MATCH (s:Skill {name: $name})-[r:similar_to]-(similar:Skill)
        RETURN similar.name, similar.category, r.similarity
        ORDER BY r.similarity DESC
        LIMIT $limit
        """
        try:
            with self._get_session() as session:
                result = session.run(cypher, name=skill_name, limit=limit)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"查询相似技能失败: {e}")
            return []

    def find_path_between_skills(self, skill_a: str, skill_b: str) -> list[dict]:
        """查找两个技能之间的最短路径"""
        cypher = """
        MATCH path = shortestPath(
            (a:Skill {name: $a})-[*..6]-(b:Skill {name: $b})
        )
        RETURN [n IN nodes(path) | n.name] AS skill_path,
               [r IN relationships(path) | type(r)] AS relations,
               length(path) AS distance
        """
        try:
            with self._get_session() as session:
                result = session.run(cypher, a=skill_a, b=skill_b)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"查找路径失败: {e}")
            return []

    def get_all_jobs(self, status: str = "all") -> list[dict]:
        """获取所有岗位"""
        if status and status != "all":
            cypher = """
            MATCH (j:Job)
            WHERE j.status = $status
            RETURN j.title AS title, j.domain AS domain, j.status AS status,
                   j.demand_trend AS demand_trend,
                   j.avg_salary_min AS avg_salary_min,
                   j.avg_salary_max AS avg_salary_max,
                   j.last_updated AS last_updated
            ORDER BY j.last_updated DESC
            """
        else:
            cypher = """
            MATCH (j:Job)
            RETURN j.title AS title, j.domain AS domain, j.status AS status,
                   j.demand_trend AS demand_trend,
                   j.avg_salary_min AS avg_salary_min,
                   j.avg_salary_max AS avg_salary_max,
                   j.last_updated AS last_updated
            ORDER BY j.last_updated DESC
            """
        try:
            with self._get_session() as session:
                result = session.run(cypher, status=status)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"查询岗位列表失败: {e}")
            return []

    def get_all_skills(self, domain: Optional[str] = None, limit: int = 200) -> list[dict]:
        """获取所有技能（可选按领域过滤）"""
        if domain:
            cypher = """
            MATCH (s:Skill)-[:belongs_to]->(d:Domain {name: $domain})
            RETURN s.name, s.category, s.difficulty, s.trend_score,
                   s.lifecycle, s.confidence
            ORDER BY s.trend_score DESC
            LIMIT $limit
            """
            params = {"domain": domain, "limit": limit}
        else:
            cypher = """
            MATCH (s:Skill)
            RETURN s.name, s.category, s.domain, s.difficulty,
                   s.trend_score, s.lifecycle, s.confidence
            ORDER BY s.trend_score DESC
            LIMIT $limit
            """
            params = {"limit": limit}

        try:
            with self._get_session() as session:
                result = session.run(cypher, **params)
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"查询技能列表失败: {e}")
            return []

    def get_graph_stats(self) -> dict:
        """获取图谱统计信息"""
        stats_cyphers = {
            "total_nodes": "MATCH (n) RETURN count(n) AS count",
            "skill_nodes": "MATCH (s:Skill) RETURN count(s) AS count",
            "job_nodes": "MATCH (j:Job) RETURN count(j) AS count",
            "domain_nodes": "MATCH (d:Domain) RETURN count(d) AS count",
            "person_nodes": "MATCH (p:Person) RETURN count(p) AS count",
            "total_relations": "MATCH ()-[r]->() RETURN count(r) AS count",
            "requires_relations": "MATCH ()-[r:requires]->() RETURN count(r) AS count",
        }
        stats = {}
        try:
            with self._get_session() as session:
                for key, cypher in stats_cyphers.items():
                    result = session.run(cypher).single()
                    stats[key] = result["count"] if result else 0
        except Exception as e:
            logger.error(f"获取图谱统计失败: {e}")
        return stats

    def get_subgraph_for_job(self, job_title: str, depth: int = 2) -> dict:
        """获取岗位相关的子图（用于可视化）"""
        cypher = f"""
        MATCH (j:Job {{title: $title}})[*1..{depth}]-(related)
        OPTIONAL MATCH (j)-[r1]->(s:Skill)
        OPTIONAL MATCH (s)-[r2]-(connected)
        RETURN {{
            nodes: collect(DISTINCT related),
            edges: collect(DISTINCT r2)
        }}
        """
        try:
            with self._get_session() as session:
                result = session.run(cypher, title=job_title).single()
                return result[0] if result else {"nodes": [], "edges": []}
        except Exception as e:
            logger.error(f"获取子图失败: {e}")
            return {"nodes": [], "edges": []}

    def get_orphan_skills(self) -> list[str]:
        """获取孤立技能（没有任何岗位要求它们的技能）"""
        cypher = """
        MATCH (s:Skill)
        WHERE NOT (s)<-[:requires]-()
        RETURN s.name AS name
        ORDER BY s.name
        LIMIT 100
        """
        try:
            with self._get_session() as session:
                result = session.run(cypher)
                return [record["name"] for record in result if record]
        except Exception as e:
            logger.error(f"查询孤立技能失败: {e}")
            return []

    def execute_query(self, cypher: str, params: dict = None) -> list[dict]:
        """执行自定义Cypher查询"""
        try:
            with self._get_session() as session:
                result = session.run(cypher, params or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"执行查询失败: {e}\nCypher: {cypher}")
            return []

    def initialize_schema(self):
        """初始化图谱Schema（创建约束和索引）"""
        operations = [
            # 节点唯一约束
            "CREATE CONSTRAINT skill_name_unique IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT job_title_unique IF NOT EXISTS FOR (j:Job) REQUIRE j.title IS UNIQUE",
            "CREATE CONSTRAINT domain_name_unique IF NOT EXISTS FOR (d:Domain) REQUIRE d.name IS UNIQUE",
            "CREATE CONSTRAINT person_hash_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.resume_hash IS UNIQUE",

            # 索引
            "CREATE INDEX skill_category_index IF NOT EXISTS FOR (s:Skill) ON (s.category)",
            "CREATE INDEX skill_domain_index IF NOT EXISTS FOR (s:Skill) ON (s.domain)",
            "CREATE INDEX skill_lifecycle_index IF NOT EXISTS FOR (s:Skill) ON (s.lifecycle)",
            "CREATE INDEX skill_trend_index IF NOT EXISTS FOR (s:Skill) ON (s.trend_score)",
            "CREATE INDEX job_status_index IF NOT EXISTS FOR (j:Job) ON (j.status)",
            "CREATE INDEX job_domain_index IF NOT EXISTS FOR (j:Job) ON (j.domain)",
        ]

        try:
            with self._get_session() as session:
                for op in operations:
                    try:
                        session.run(op)
                    except Exception as idx_e:
                        # 约束可能已存在，忽略
                        logger.debug(f"Schema初始化操作: {idx_e}")
            logger.info("图谱Schema初始化完成")
        except Exception as e:
            logger.error(f"Schema初始化失败: {e}")

    def seed_initial_domains(self):
        """初始化基础领域数据"""
        from models.skill_taxonomy import DOMAINS

        for domain_name, domain_data in DOMAINS.items():
            self.create_domain_node(domain_name, description=domain_data["description"])

            # 创建该领域下的技能节点
            for cat_name, skills in domain_data["subcategories"].items():
                for skill in skills:
                    from models.graph_nodes import SkillCategory, SkillDomain, LifecycleStage

                    # 映射领域枚举
                    try:
                        domain_enum = SkillDomain(domain_name)
                    except ValueError:
                        domain_enum = SkillDomain.SOFTWARE_DEVELOPMENT

                    self.create_skill_node({
                        "name": skill,
                        "category": cat_name,
                        "domain": domain_enum.value if isinstance(domain_enum, SkillDomain) else domain_name,
                        "difficulty": 5,
                        "trend_score": 0.0,
                        "lifecycle": LifecycleStage.MATURE.value,
                        "version": "1.0",
                        "confidence": 0.9,
                        "sources": ["taxonomy_init"],
                        "description": f"{domain_name}领域的{cat_name}技能"
                    })

                    # 创建归属关系
                    self.create_belongs_to_relation(skill, domain_name)

        logger.info(f"初始领域数据种子完成，共{len(DOMAINS)}个领域")


# 全局单例
_graph_service: Optional[GraphService] = None


def get_graph_service() -> GraphService:
    """获取图谱服务单例"""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service
