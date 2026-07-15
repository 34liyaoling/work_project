"""生成 data/raw/ 下的样例 JSONL 数据

本脚本在 ``data/raw/`` 目录生成 5 个样例文件，每个文件 20~30 条 JD：
* boss_sample.jsonl        - BOSS直聘
* zhilian_sample.jsonl     - 智联招聘
* liepin_sample.jsonl      - 猎聘
* enterprise_sample.jsonl  - 企业官网
* onet_sample.jsonl        - O*NET

数据由 :mod:`app.services.mock_data` 生成，模拟真实 JD 风格。
"""
from __future__ import annotations

import json
import os
import sys
from typing import List

# 加入项目根目录
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def write_jsonl(path: str, items: List[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"Wrote {len(items)} records to {path}")


def main() -> None:
    from app.services.mock_data import MockJDGenerator
    from app.services.crawler.onet_crawler import ONET_STANDARD_SKILLS

    gen = MockJDGenerator(seed=2026)

    # BOSS 直聘
    items = gen.generate(30, source="boss")
    write_jsonl(r"d:\work\competency-graph\backend\data\raw\boss_sample.jsonl", [it.to_dict() for it in items])

    # 智联招聘
    items = gen.generate(25, source="zhilian")
    write_jsonl(r"d:\work\competency-graph\backend\data\raw\zhilian_sample.jsonl", [it.to_dict() for it in items])

    # 猎聘
    items = gen.generate(20, source="liepin")
    write_jsonl(r"d:\work\competency-graph\backend\data\raw\liepin_sample.jsonl", [it.to_dict() for it in items])

    # 企业官网
    items = gen.generate(20, source="enterprise")
    write_jsonl(r"d:\work\competency-graph\backend\data\raw\enterprise_sample.jsonl", [it.to_dict() for it in items])

    # O*NET（不同结构：技能条目而非 JD）
    onet_items = []
    for i, skill in enumerate(ONET_STANDARD_SKILLS[:50]):
        onet_items.append({
            "jd_id": f"onet-{i:04d}",
            "source": "onet",
            "source_url": f"https://www.onetonline.org/find/descriptor/result/2.A.1?keyword={skill}",
            "title": skill,
            "category": "技能图谱",
            "skills": [skill],
            "raw_text": f"O*NET standard skill: {skill}",
            "published_at": None,
        })
    write_jsonl(r"d:\work\competency-graph\backend\data\raw\onet_sample.jsonl", onet_items)

    # 行业报告
    items = gen.generate(15, source="industry_report")
    write_jsonl(r"d:\work\competency-graph\backend\data\raw\industry_sample.jsonl", [it.to_dict() for it in items])

    # 政策文件
    items = gen.generate(10, source="policy")
    write_jsonl(r"d:\work\competency-graph\backend\data\raw\policy_sample.jsonl", [it.to_dict() for it in items])

    print("\nAll sample JSONL files written.")


if __name__ == "__main__":
    main()
