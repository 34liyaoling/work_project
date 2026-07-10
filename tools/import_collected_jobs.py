"""导入 docs 下采集的岗位数据到知识图谱

用法:
    cd knowledge-graph-system
    python -m tools.import_collected_jobs            # 导入并构建图谱
    python -m tools.import_collected_jobs --dry-run  # 仅预览补全结果，不写入图谱

数据来源:
    docs/boss_zhipin_jobs.json
    docs/zhaopin_jobs(1).json

策略:
    不调用 LLM，基于岗位标题关键词匹配 JOB_SKILL_MAP 补全技能。
    非技术岗（数据标注/市场/销售/讲师/助教等）不硬塞技术技能。
"""

import argparse
import glob
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ===== 岗位标题 -> 技能 映射规则 =====
# 按顺序匹配，先命中的优先；关键词全部小写匹配。
# 设计原则：只给真正的技术岗匹配技能，非技术岗留空。
JOB_SKILL_MAP: list[tuple[list[str], list[str]]] = [
    # --- 大模型 / LLM / Agent ---
    (["大模型", "llm", "large language"], ["Python", "LangChain", "Prompt Engineering",
        "RAG系统设计", "Fine-tuning", "Transformer"]),
    (["agent", "智能体"], ["Python", "LangChain", "LangGraph", "Function Calling",
        "ReAct模式", "多智能体协作"]),
    (["aigc"], ["Python", "LangChain", "Prompt Engineering", "图像生成(Diffusion/GAN)"]),
    (["文心一言", "千问", "通义", "deepseek", "llama"], ["Python", "LangChain",
        "大语言模型", "Fine-tuning"]),

    # --- 算法细分方向 ---
    (["nlp", "自然语言"], ["Python", "BERT", "Transformer", "分词", "命名实体识别",
        "信息抽取"]),
    (["视觉", "cv", "图像算法", "图像视觉", "视觉算法"], ["PyTorch", "CNN",
        "目标检测(YOLO/RCNN)", "图像分割", "Transformer"]),
    (["多模态"], ["PyTorch", "Transformer", "多模态", "NLP", "计算机视觉"]),
    (["推荐算法", "广告算法", "搜索算法", "交易算法"], ["Python", "Scikit-learn",
        "机器学习", "特征工程", "XGBoost"]),
    (["强化学习", "rl"], ["Python", "PyTorch", "深度学习"]),
    (["语音", "asr", "tts"], ["Python", "Transformer", "对话系统"]),

    # --- 通用算法/机器学习/深度学习工程师 ---
    (["算法工程师", "算法研究员", "算法实习", "算法研究",
      "机器学习", "深度学习"], ["Python", "PyTorch", "TensorFlow", "机器学习",
        "深度学习", "Scikit-learn"]),

    # --- 数据方向 ---
    (["数据挖掘"], ["Python", "机器学习", "Scikit-learn", "数据可视化(Tableau/PowerBI/Matplotlib)"]),
    (["数据分析"], ["Python", "SQL高级查询", "Pandas", "NumPy", "统计分析",
        "数据可视化(Tableau/PowerBI/Matplotlib)"]),
    (["大数据", "数据开发", "数据工程"], ["Spark", "Flink", "Hadoop/MapReduce",
        "Hive", "Kafka", "ETL/ELT"]),
    (["数仓", "数据仓库"], ["Hive", "SQL高级查询", "ETL/ELT", "维度建模"]),
    (["etl"], ["SQL高级查询", "ETL/ELT", "Airflow"]),

    # --- 开发方向 ---
    (["python"], ["Python", "Python/FastAPI/Django/Flask"]),
    (["java"], ["Java", "Java/Spring Boot", "MySQL"]),
    (["go语言", "golang", " go "], ["Go", "Go/Gin"]),
    (["c++", "c/c++"], ["C++"]),
    (["前端", "web前端", "前端开发"], ["React/Vue/Angular", "TypeScript",
        "JavaScript", "HTML", "CSS"]),
    (["全栈"], ["React/Vue/Angular", "Node.js", "Python/FastAPI/Django/Flask"]),
    (["后端", "服务端", "服务端开发"], ["Java/Spring Boot", "Python/FastAPI/Django/Flask",
        "MySQL", "Redis"]),
    (["爬虫"], ["Python", "Scrapy"]),
    (["量化"], ["Python", "Pandas", "NumPy", "统计分析"]),

    # --- 测试 ---
    (["测试开发", "测试工程师"], ["Python", "Java", "自动化测试"]),

    # --- 运维 / DevOps / SRE ---
    (["运维", "devops", "sre"], ["Linux", "Docker", "Kubernetes",
        "Prometheus", "Grafana"]),
    (["gpu调度", "gpu"], ["Docker", "Kubernetes", "Linux"]),

    # --- 嵌入式 / 硬件 / 机器人 ---
    (["嵌入式"], ["C++", "嵌入式Linux", "RTOS"]),
    (["ros", "机器人"], ["C++", "Python", "ROS"]),
    (["硬件", "ic前端", "光学"], []),  # 硬件岗不匹配软件技能

    # --- 游戏 ---
    (["unity", "游戏开发"], ["C#", "C++"]),
    (["游戏测试"], ["Python"]),

    # --- 安全 ---
    (["安全算法", "安全研究", "安全分析"], ["Python", "渗透测试", "漏洞挖掘"]),
    (["风控"], ["Python", "机器学习", "Scikit-learn"]),

    # --- 云计算 / 架构 ---
    (["云原生", "云架构", "k8s", "kubernetes"], ["Docker", "Kubernetes", "Terraform"]),
    (["架构师"], ["微服务架构", "分布式系统", "API设计(RESTful/GraphQL/gRPC)"]),

    # --- 导航/自动驾驶 ---
    (["slam", "导航算法", "自动驾驶", "感知算法"], ["C++", "Python", "PyTorch",
        "目标检测(YOLO/RCNN)"]),
]

# 非技术岗关键词：命中则不分配技能
NON_TECH_KEYWORDS = [
    "数据标注", "标注员", "训练师", "数据采集员", "采集员", "场景训练",
    "产品经理", "产品顾问", "课程顾问", "解决方案经理", "售前", "售后",
    "市场", "销售", "业务员", "业务线", "招商", "营销", "投放", "竞价",
    "媒介", "客户经理", "客户执行", "ae", "公关", "项目经理",
    "讲师", "助教", "老师", "班主任", "教务", "教研室", "院长", "副院长",
    "带头人", "学科带头", "专业负责", "教学", "录题", "带背",
    "剪辑", "摄影", "主持", "播音", "短视频", "视频审核", "视频生成应用",
    "舞蹈", "音乐", "美术", "艺术",
    "管培生", "储备管理", "内训师", "台球", "房管", "房屋", "房源",
    "住宿", "宿舍", "普工", "操作工", "电气设计", "焊接", "机械设计",
    "非标机械", "材料", "光学工程", "通信技术支持",
    "人力资源", "行政", "财务", "法务", "专利代理",
    "实验员", "博士后", "院长", "主任", "经理", "总监", "负责人", "首席",
    "副校长", "老师", "教研", "咨询", "顾问", "策划",
]


def _title_matches(title: str, keywords: list[str]) -> bool:
    """标题是否命中任一关键词"""
    t = title.lower()
    return any(kw in t for kw in keywords)


def infer_skills(job_title: str) -> list[str]:
    """根据岗位标题推断技能列表"""
    if not job_title:
        return []

    # 非技术岗：不分配技能
    if _title_matches(job_title, NON_TECH_KEYWORDS):
        return []

    # 按规则顺序匹配，命中即返回
    for keywords, skills in JOB_SKILL_MAP:
        if _title_matches(job_title, keywords):
            return list(skills)

    # 未匹配的岗位：如果标题含"工程师/开发/软件"但无具体方向，给通用开发技能
    t = job_title.lower()
    if any(kw in t for kw in ["工程师", "开发", "软件", "程序"]):
        if any(kw in t for kw in ["人工智能", "ai"]):
            return ["Python", "机器学习", "PyTorch"]
        return ["Python", "Java", "SQL高级查询"]

    return []


def load_jobs() -> list[dict]:
    """读取 docs 下所有采集文件"""
    docs_dir = Path(__file__).parent.parent / "docs"
    files = list(docs_dir.glob("boss_zhipin_jobs.json")) + \
            list(docs_dir.glob("zhaopin_jobs*.json"))

    all_jobs = []
    for f in files:
        logger.info(f"读取文件: {f.name}")
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        jobs = data.get("jobs", [])
        logger.info(f"  -> {len(jobs)} 条岗位 (source: {data.get('source', 'unknown')})")
        all_jobs.extend(jobs)

    return all_jobs


def deduplicate(jobs: list[dict]) -> list[dict]:
    """基于标题+公司名去重"""
    seen = set()
    unique = []
    for j in jobs:
        key = (j.get("job_title", "").strip().lower(),
               j.get("company_name", "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(j)
    return unique


def enrich_skills(jobs: list[dict]) -> tuple[list[dict], dict]:
    """补全空技能岗位，返回 (增强后列表, 统计)"""
    enriched = 0
    kept_original = 0
    left_empty = 0

    for job in jobs:
        existing = job.get("skills") or []
        if existing:
            kept_original += 1
            continue

        inferred = infer_skills(job.get("job_title", ""))
        if inferred:
            job["skills"] = inferred
            enriched += 1
        else:
            left_empty += 1

    return jobs, {
        "kept_original_skills": kept_original,
        "enriched_by_map": enriched,
        "left_empty_non_tech": left_empty,
    }


def build_graph(jobs: list[dict]) -> dict:
    """调用 GraphBuilderAgent 构建知识图谱"""
    from agents.graph_builder import GraphBuilderAgent
    builder = GraphBuilderAgent()
    result = builder.build_from_data(jobs)
    return result


def main():
    parser = argparse.ArgumentParser(description="导入采集的岗位数据到知识图谱")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅预览技能补全结果，不写入图谱")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("开始导入采集数据")
    logger.info("=" * 60)

    # 1. 读取数据
    jobs = load_jobs()
    logger.info(f"共读取 {len(jobs)} 条原始岗位")

    # 2. 去重
    jobs = deduplicate(jobs)
    logger.info(f"去重后 {len(jobs)} 条唯一岗位")

    # 3. 技能补全
    jobs, stats = enrich_skills(jobs)
    logger.info(f"技能补全统计:")
    logger.info(f"  保留原始技能:  {stats['kept_original_skills']} 条")
    logger.info(f"  MAP补全:       {stats['enriched_by_map']} 条")
    logger.info(f"  非技术岗留空:  {stats['left_empty_non_tech']} 条")

    # 保存增强后的数据快照
    snapshot_dir = Path("data/import")
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_file = snapshot_dir / "collected_enriched.json"
    with open(snapshot_file, "w", encoding="utf-8") as f:
        json.dump({
            "total": len(jobs),
            "stats": stats,
            "jobs": jobs,
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"增强数据快照已保存: {snapshot_file}")

    if args.dry_run:
        logger.info("--dry-run 模式，不写入图谱。预览完成。")
        _print_preview(jobs)
        return

    # 4. 构建知识图谱
    logger.info("开始构建知识图谱...")
    result = build_graph(jobs)
    logger.info("=" * 60)
    logger.info("导入完成!")
    logger.info(f"  岗位写入:      {result.get('jobs_updated', 0)}")
    logger.info(f"  技能关系:      {result.get('skills_added', 0)}")
    infer = result.get("inferred_relations", {})
    logger.info(f"  推断关系:      {infer.get('total_relations', 0)} "
                f"(先修{infer.get('prerequisite_created', 0)}, "
                f"归属{infer.get('belongs_to_created', 0)}, "
                f"相似{infer.get('similar_to_created', 0)})")
    logger.info("=" * 60)


def _print_preview(jobs: list[dict]):
    """预览前20条技能补全结果"""
    print("\n" + "=" * 60)
    print("技能补全预览 (前20条带技能的岗位):")
    print("=" * 60)
    count = 0
    for j in jobs:
        if j.get("skills"):
            print(f"  {j['job_title'][:30]:30s} -> {', '.join(j['skills'])}")
            count += 1
            if count >= 20:
                break
    print("=" * 60)


if __name__ == "__main__":
    main()
