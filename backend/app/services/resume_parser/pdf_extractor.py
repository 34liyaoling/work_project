"""PDF 文本提取

基于 PyMuPDF（fitz），支持多栏布局（左→右栏分块后再合并）。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from app.core.logger import log


try:
    import fitz  # type: ignore  # PyMuPDF
    HAS_PYMUPDF = True
except Exception:  # pragma: no cover
    fitz = None  # type: ignore
    HAS_PYMUPDF = False


class PDFExtractor:
    """PDF 简历文本提取器"""

    def extract(self, file_path: str) -> Dict[str, Any]:
        """提取 PDF 文本与基础元数据"""
        if not os.path.exists(file_path):
            log.error(f"PDF 文件不存在: {file_path}")
            return {"text": "", "pages": 0, "blocks": [], "error": "file_not_found"}
        if not HAS_PYMUPDF:
            return self._mock_extract(file_path)
        try:
            doc = fitz.open(file_path)
            blocks: List[Dict[str, Any]] = []
            full_text: List[str] = []
            for page_idx, page in enumerate(doc):
                page_text = page.get_text("text") or ""
                # 简单分栏检测：根据文本块的 x 坐标中位数划分左右栏
                try:
                    raw_dict = page.get_text("dict")
                except Exception:
                    raw_dict = {"blocks": []}
                left_col, right_col = self._split_columns(raw_dict)
                if left_col and right_col:
                    ordered = "\n".join(left_col + right_col)
                else:
                    ordered = page_text
                full_text.append(ordered)
                blocks.append({"page": page_idx, "text": ordered})
            doc.close()
            return {
                "text": "\n".join(full_text),
                "pages": len(full_text),
                "blocks": blocks,
            }
        except Exception as e:
            log.error(f"PyMuPDF 解析失败: {e}")
            return self._mock_extract(file_path)

    def extract_bytes(self, data: bytes, file_name: str = "uploaded.pdf") -> Dict[str, Any]:
        """从内存字节流解析"""
        if not HAS_PYMUPDF:
            return {"text": "", "pages": 0, "blocks": [], "error": "pymupdf_unavailable"}
        try:
            doc = fitz.open(stream=data, filetype="pdf")
            full_text = [page.get_text("text") or "" for page in doc]
            doc.close()
            return {"text": "\n".join(full_text), "pages": len(full_text), "blocks": []}
        except Exception as e:
            log.error(f"PyMuPDF 字节流解析失败: {e}")
            return {"text": "", "pages": 0, "blocks": [], "error": str(e)}

    # ----------------- 内部 -----------------
    @staticmethod
    def _split_columns(page_dict: Dict[str, Any]) -> (List[str], List[str]):
        """根据 x 坐标中位数分左右栏"""
        try:
            page_width = page_dict.get("width", 0) or page_dict.get("bbox", [0, 0, 0, 0])[2] or 0
        except Exception:
            page_width = 0
        if not page_width:
            return [], []
        threshold = page_width / 2
        left: List[str] = []
        right: List[str] = []
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            bbox = block.get("bbox", [0, 0, 0, 0])
            x0 = bbox[0]
            lines_text: List[str] = []
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                line_str = "".join(s.get("text", "") for s in spans)
                lines_text.append(line_str)
            block_text = "\n".join(lines_text)
            if x0 < threshold:
                left.append(block_text)
            else:
                right.append(block_text)
        return left, right

    @staticmethod
    def _mock_extract(file_path: str) -> Dict[str, Any]:
        log.warning("PyMuPDF 未安装, 返回空 PDF 结果")
        return {
            "text": f"[MOCK PDF] {os.path.basename(file_path)}",
            "pages": 1,
            "blocks": [],
            "mock": True,
        }


_singleton: Optional[PDFExtractor] = None


def get_pdf_extractor() -> PDFExtractor:
    global _singleton
    if _singleton is None:
        _singleton = PDFExtractor()
    return _singleton
