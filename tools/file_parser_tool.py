"""文件解析工具 - 支持多种格式"""

import json
import logging
from pathlib import Path
from typing import Optional
from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


class FileParserTool(BaseTool):
    """多格式文件解析工具"""
    name: str = "file_parser"
    description: str = "解析PDF、DOCX、TXT、图片等格式的文件内容"

    def _run(self, file_path: str) -> str:
        """解析文件"""
        path = Path(file_path)
        if not path.exists():
            return json.dumps({"error": f"文件不存在: {file_path}"})

        file_type = path.suffix.lower().replace(".", "")
        text = ""

        try:
            if file_type == "pdf":
                import fitz
                doc = fitz.open(file_path)
                for page in doc:
                    text += page.get_text() + "\n"
                doc.close()
            elif file_type == "docx":
                from docx import Document
                doc = Document(file_path)
                for para in doc.paragraphs:
                    text += para.text + "\n"
            elif file_type in ("txt", "md"):
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            else:
                with open(file_path, "rb") as f:
                    header = f.read(1024)
                    text = f"[二进制文件，大小: {path.stat().st_size} bytes]"
        except Exception as e:
            return json.dumps({"error": str(e), "file_type": file_type})

        return json.dumps({
            "success": True,
            "file_type": file_type,
            "text_length": len(text),
            "text_preview": text[:2000],
            "full_text": text if len(text) <= 10000 else text[:10000] + "\n...(截断)",
        }, ensure_ascii=False)
