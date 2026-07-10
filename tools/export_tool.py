"""导出工具 - 报告导出功能"""

import json
import os
import logging
from datetime import datetime
from typing import Optional
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "data", "exports")


class ExportTool(BaseTool):
    """数据导出工具 - 支持多种格式导出"""
    name: str = "export"
    description: str = "将分析结果导出为JSON/Markdown/CSV等格式"

    def _run(self, data: dict, format_type: str = "json", filename: str = None) -> str:
        """导出数据"""
        os.makedirs(EXPORT_DIR, exist_ok=True)

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}.{format_type}"

        filepath = os.path.join(EXPORT_DIR, filename)

        try:
            if format_type == "json":
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            elif format_type == "markdown":
                content = self._to_markdown(data)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)

            elif format_type == "csv":
                import csv
                with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys() if isinstance(data, list) else data.keys())
                    writer.writeheader()
                    if isinstance(data, list):
                        writer.writerows(data)
                    else:
                        writer.writerow(data)

            else:
                return json.dumps({"error": f"不支持的格式: {format_type}"})

            return json.dumps({
                "success": True,
                "filepath": filepath,
                "size_bytes": os.path.getsize(filepath),
            }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({"error": str(e)})

    def _to_markdown(self, data: dict) -> str:
        """将数据转为Markdown格式"""
        lines = ["# 分析报告\n"]
        lines.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        def render_dict(d, indent=0):
            prefix = "  " * indent
            for k, v in d.items():
                if isinstance(v, dict):
                    lines.append(f"{prefix}- **{k}**:")
                    render_dict(v, indent + 1)
                elif isinstance(v, list):
                    lines.append(f"{prefix}- **{k}**:")
                    for item in v[:10]:
                        lines.append(f"{prefix}  - {item}")
                else:
                    lines.append(f"{prefix}- **{k}**: {v}")

        render_dict(data)
        return "\n".join(lines)
