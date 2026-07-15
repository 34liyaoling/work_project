"""生成测试数据 (≥100 JD, ≥20 简历, ≥20 匹配对)

运行：
    python -m tests.test_data.generate
"""
import json
import random
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent

LEVELS = ["初级", "中级", "高级", "资深"]
CITIES = ["北京", "上海", "深圳", "杭州", "广州", "成都"]
SOURCES = ["lagou", "zhipin", "liepin", "51job"]
CATEGORIES = ["后端", "前端", "数据", "算法", "测试", "运维", "产品", "运营"]


SKILL_BANK = {
    "后端": ["Python", "Java", "Go", "MySQL", "Redis", "Kafka", "Spring Boot", "Django", "Docker", "Kubernetes"],
    "前端": ["JavaScript", "TypeScript", "React", "Vue", "Webpack", "CSS", "HTML5", "Node.js", "Vite"],
    "数据": ["SQL", "Python", "Spark", "Flink", "Hadoop", "Hive", "Airflow", "Kafka", "ClickHouse"],
    "算法": ["Python", "PyTorch", "TensorFlow", "机器学习", "深度学习", "NLP", "推荐系统", "NumPy", "Pandas"],
    "测试": ["Python", "Selenium", "Pytest", "JMeter", "Postman", "Jenkins", "Linux"],
    "运维": ["Linux", "Docker", "Kubernetes", "Ansible", "Terraform", "Prometheus", "Grafana", "Nginx"],
    "产品": ["Axure", "Figma", "用户调研", "数据分析", "SQL", "PPT"],
    "运营": ["数据分析", "SQL", "Excel", "用户增长", "内容运营"],
}

COMPANIES = [
    "字节跳动", "阿里巴巴", "腾讯", "美团", "京东", "小米", "华为",
    "百度", "网易", "滴滴", "快手", "B站", "小红书", "贝壳",
    "示例科技公司", "示例互联网公司", "示例智能公司",
]


def gen_jd(idx: int) -> dict:
    rng = random.Random(idx)
    cat = rng.choice(CATEGORIES)
    skills_pool = SKILL_BANK[cat]
    skills = rng.sample(skills_pool, k=min(rng.randint(4, 7), len(skills_pool)))
    level = rng.choice(LEVELS)
    city = rng.choice(CITIES)
    src = rng.choice(SOURCES)
    company = rng.choice(COMPANIES)
    title_prefix = {"后端": "后端开发工程师", "前端": "前端开发工程师", "数据": "数据工程师",
                    "算法": "算法工程师", "测试": "测试开发工程师", "运维": "运维工程师",
                    "产品": "产品经理", "运营": "运营专员"}[cat]
    return {
        "jd_id": f"JD-{idx:05d}",
        "source": src,
        "company": company,
        "title": f"{level}{title_prefix}",
        "category": cat,
        "level": level,
        "location": city,
        "salary_range": f"{rng.randint(10, 80)}-{rng.randint(20, 100)}K",
        "skills": skills,
        "published_at": f"2025-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}",
        "raw_text": (
            f"【{company}】招聘{level}{title_prefix}，工作地 {city}\n"
            f"职责：\n1. 负责{cat}方向的开发；\n2. 参与系统设计与优化。\n"
            f"要求：\n1. 熟练掌握 {', '.join(skills[:3])}；\n"
            f"2. 有 {', '.join(skills[3:])} 经验者优先。"
        ),
    }


def gen_resume(idx: int) -> dict:
    rng = random.Random(idx * 17 + 3)
    cat = rng.choice(CATEGORIES)
    skills_pool = SKILL_BANK[cat]
    skills = rng.sample(skills_pool, k=min(rng.randint(3, 6), len(skills_pool)))
    years = rng.randint(1, 10)
    return {
        "resume_id": f"R-{idx:04d}",
        "name": f"测试候选人{idx}",
        "category": cat,
        "years": years,
        "skills": skills,
        "raw_text": (
            f"姓名：测试候选人{idx} | 意向岗位：{cat} | 经验{years}年\n"
            f"技能：{', '.join(skills)}\n"
            f"工作经历：在示例公司担任{cat}工程师。"
        ),
    }


def gen_match_pairs(n: int = 25) -> list:
    rng = random.Random(2024)
    pairs = []
    for i in range(n):
        jd_idx = rng.randint(1, 100)
        r_idx = rng.randint(1, 30)
        # 50% 期望匹配（同类别 + 重叠技能 >= 50%）
        if rng.random() < 0.5:
            jd = gen_jd(jd_idx)
            # 强制类别一致
            cat = jd["category"]
            r = gen_resume(r_idx)
            r["category"] = cat
            # 50% 重叠
            overlap = max(1, len(jd["skills"]) // 2)
            r["skills"] = jd["skills"][:overlap] + r["skills"][overlap:]
            expected = True
        else:
            jd = gen_jd(jd_idx)
            r = gen_resume(r_idx)
            expected = False
        pairs.append({
            "resume_id": r["resume_id"],
            "jd_id": jd["jd_id"],
            "expected_match": expected,
        })
    return pairs


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jds = [gen_jd(i) for i in range(1, 121)]  # 120 条
    resumes = [gen_resume(i) for i in range(1, 31)]  # 30 份
    matches = gen_match_pairs(30)  # 30 对

    with (OUT_DIR / "jd_corpus.json").open("w", encoding="utf-8") as f:
        json.dump(jds, f, ensure_ascii=False, indent=2)
    with (OUT_DIR / "resume_corpus.json").open("w", encoding="utf-8") as f:
        json.dump(resumes, f, ensure_ascii=False, indent=2)
    with (OUT_DIR / "match_pairs.json").open("w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)

    print(f"生成完成: JD={len(jds)} 简历={len(resumes)} 匹配对={len(matches)}")


if __name__ == "__main__":
    main()
