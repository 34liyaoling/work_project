// =============================================================
// CompetencyGraph Neo4j 初始化 Cypher
// 图谱 Schema：节点（JobRole/Skill/Tool/Industry）+ 关系
// =============================================================

// -------------------------------------------------------------
// 1. 唯一性约束
// -------------------------------------------------------------
CREATE CONSTRAINT jobrole_name IF NOT EXISTS FOR (n:JobRole) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (n:Skill) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT tool_name IF NOT EXISTS FOR (n:Tool) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT industry_name IF NOT EXISTS FOR (n:Industry) REQUIRE n.name IS UNIQUE;

// -------------------------------------------------------------
// 2. 索引（加速查询）
// -------------------------------------------------------------
CREATE INDEX skill_category IF NOT EXISTS FOR (n:Skill) ON (n.category);
CREATE INDEX skill_popularity IF NOT EXISTS FOR (n:Skill) ON (n.popularity);
CREATE INDEX skill_level IF NOT EXISTS FOR (n:Skill) ON (n.level);
CREATE INDEX jobrole_category IF NOT EXISTS FOR (n:JobRole) ON (n.category);
CREATE INDEX jobrole_level IF NOT EXISTS FOR (n:JobRole) ON (n.level);
CREATE INDEX jobrole_is_new IF NOT EXISTS FOR (n:JobRole) ON (n.is_new);
CREATE INDEX jobrole_confidence IF NOT EXISTS FOR (n:JobRole) ON (n.confidence);

// -------------------------------------------------------------
// 3. 样例数据（演示用，可选）
// -------------------------------------------------------------
// 岗位
MERGE (j1:JobRole {name: '算法工程师'})
  ON CREATE SET j1.category = '算法',
                j1.level = '高级',
                j1.confidence = 0.95,
                j1.description = '负责核心算法研发与落地',
                j1.is_new = 0;

MERGE (j2:JobRole {name: '前端工程师'})
  ON CREATE SET j2.category = '前端',
                j2.level = '中级',
                j2.confidence = 0.92,
                j2.description = '负责 Web 端产品研发',
                j2.is_new = 0;

MERGE (j3:JobRole {name: 'AI Agent 工程师'})
  ON CREATE SET j3.category = 'AI',
                j3.level = '高级',
                j3.confidence = 0.75,
                j3.description = '基于 LLM 构建 Agent 系统',
                j3.is_new = 1;

// 技能
MERGE (s1:Skill {name: 'Python'})
  ON CREATE SET s1.category = '编程语言', s1.popularity = 0.95, s1.level = 'advanced';
MERGE (s2:Skill {name: '机器学习'})
  ON CREATE SET s2.category = 'AI', s2.popularity = 0.88, s2.level = 'advanced';
MERGE (s3:Skill {name: '深度学习'})
  ON CREATE SET s3.category = 'AI', s3.popularity = 0.82, s3.level = 'advanced';
MERGE (s4:Skill {name: 'JavaScript'})
  ON CREATE SET s4.category = '编程语言', s4.popularity = 0.90, s4.level = 'intermediate';
MERGE (s5:Skill {name: 'Vue'})
  ON CREATE SET s5.category = '前端框架', s5.popularity = 0.85, s5.level = 'intermediate';
MERGE (s6:Skill {name: 'LangChain'})
  ON CREATE SET s6.category = 'AI框架', s6.popularity = 0.70, s6.level = 'advanced';
MERGE (s7:Skill {name: 'RAG'})
  ON CREATE SET s7.category = 'AI', s7.popularity = 0.65, s7.level = 'advanced';
MERGE (s8:Skill {name: 'MySQL'})
  ON CREATE SET s8.category = '数据库', s8.popularity = 0.88, s8.level = 'intermediate';

// 工具
MERGE (t1:Tool {name: 'VSCode'})
  ON CREATE SET t1.category = 'IDE';
MERGE (t2:Tool {name: 'Git'})
  ON CREATE SET t2.category = '版本控制';

// 行业
MERGE (i1:Industry {name: '互联网'})
  ON CREATE SET i1.category = 'tech';
MERGE (i2:Industry {name: '金融科技'})
  ON CREATE SET i2.category = 'finance';

// -------------------------------------------------------------
// 4. 关系
// -------------------------------------------------------------
// JobRole -[REQUIRES]-> Skill
MERGE (j1)-[r1:REQUIRES]->(s1) ON CREATE SET r1.weight = 1.0;
MERGE (j1)-[r2:REQUIRES]->(s2) ON CREATE SET r2.weight = 0.9;
MERGE (j1)-[r3:REQUIRES]->(s3) ON CREATE SET r3.weight = 0.8;
MERGE (j2)-[r4:REQUIRES]->(s4) ON CREATE SET r4.weight = 1.0;
MERGE (j2)-[r5:REQUIRES]->(s5) ON CREATE SET r5.weight = 0.9;
MERGE (j2)-[r6:REQUIRES]->(s8) ON CREATE SET r6.weight = 0.6;
MERGE (j3)-[r7:REQUIRES]->(s1) ON CREATE SET r7.weight = 0.9;
MERGE (j3)-[r8:REQUIRES]->(s2) ON CREATE SET r8.weight = 0.8;
MERGE (j3)-[r9:REQUIRES]->(s6) ON CREATE SET r9.weight = 0.9;
MERGE (j3)-[r10:REQUIRES]->(s7) ON CREATE SET r10.weight = 0.85;

// JobRole -[USES]-> Tool
MERGE (j1)-[:USES]->(t1);
MERGE (j1)-[:USES]->(t2);
MERGE (j2)-[:USES]->(t1);
MERGE (j2)-[:USES]->(t2);

// JobRole -[BELONGS_TO]-> Industry
MERGE (j1)-[:BELONGS_TO]->(i1);
MERGE (j2)-[:BELONGS_TO]->(i1);
MERGE (j3)-[:BELONGS_TO]->(i1);

// Skill -[DEPENDS_ON]-> Skill
MERGE (s3)-[:DEPENDS_ON]->(s2);
MERGE (s7)-[:DEPENDS_ON]->(s2);
MERGE (s6)-[:DEPENDS_ON]->(s2);
MERGE (s6)-[:DEPENDS_ON]->(s3);

// Skill -[RELATED_TO]-> Skill
MERGE (s4)-[:RELATED_TO]->(s5);

// =============================================================
// 完成
// =============================================================
