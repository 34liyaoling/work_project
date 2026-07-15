"""文本预处理器

职责：
    1. 去除 HTML 标签
    2. 去除特殊控制字符 / 不可见字符
    3. 统一全角 / 半角、空格
    4. 标准化中英文标点
    5. 保留语义信息（不强行分词 / 不丢数据）
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.logger import log


# ============================================================
# 编译正则
# ============================================================
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_ENTITY_RE = re.compile(r"&[a-zA-Z]+;|&#\d+;|&#x[0-9a-fA-F]+;")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]")
_URL_RE = re.compile(r"https?://[^\s\u4e00-\u9fff]+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"1[3-9]\d{9}")
_MULTI_SPACE_RE = re.compile(r"\s+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")

# 全角 -> 半角
_FULL2HALF_TABLE = {i: i - 0xFEE0 for i in range(0xFF01, 0xFF5E + 1)}
_FULL_SPACE_HALF = {"\u3000": " "}

# 中英文标点对照（半角 -> 中文）
_CN_PUNCT = {
    ",": "，", ".": "。", ":": "：", ";": "；",
    "!": "！", "?": "？", "(": "（", ")": "）",
    "<": "《", ">": "》", "\"": "\u201C", "'": "\u2018",
}


@dataclass
class PreprocessResult:
    """预处理结果"""

    text: str
    removed_html: int = 0
    removed_controls: int = 0
    removed_urls: int = 0
    removed_emails: int = 0
    removed_phones: int = 0
    original_length: int = 0
    cleaned_length: int = 0


class TextPreprocessor:
    """文本预处理器

    用法:
        pp = TextPreprocessor()
        out = pp.process("<p>Hello world!</p>\\n")
    """

    def __init__(
        self,
        remove_html: bool = True,
        remove_urls: bool = False,
        remove_emails: bool = False,
        remove_phones: bool = False,
        full_to_half: bool = True,
        cn_punct: bool = False,
        collapse_spaces: bool = True,
        normalize_unicode: bool = True,
    ) -> None:
        self.remove_html = remove_html
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.remove_phones = remove_phones
        self.full_to_half = full_to_half
        self.cn_punct = cn_punct
        self.collapse_spaces = collapse_spaces
        self.normalize_unicode = normalize_unicode

    # -------------------------------------------------------- 公开方法
    def process(self, text: str) -> PreprocessResult:
        """执行完整预处理链"""
        if not text:
            return PreprocessResult(text="", original_length=0, cleaned_length=0)
        original_length = len(text)
        removed_html = removed_controls = removed_urls = removed_emails = removed_phones = 0

        # 1. Unicode 标准化（NFKC：兼容分解 + 组合）
        if self.normalize_unicode:
            text = unicodedata.normalize("NFKC", text)

        # 2. 去 HTML
        if self.remove_html:
            new_text, n = _HTML_TAG_RE.subn(" ", text)
            removed_html = n
            text = new_text
            text, _ = _HTML_ENTITY_RE.subn(" ", text)

        # 3. 去控制字符
        text, n = _CONTROL_CHAR_RE.subn(" ", text)
        removed_controls = n

        # 4. 去 URL / Email / Phone
        if self.remove_urls:
            text, n = _URL_RE.subn(" ", text)
            removed_urls = n
        if self.remove_emails:
            text, n = _EMAIL_RE.subn(" ", text)
            removed_emails = n
        if self.remove_phones:
            text, n = _PHONE_RE.subn(" ", text)
            removed_phones = n

        # 5. 全角 -> 半角
        if self.full_to_half:
            text = "".join(
                _FULL2HALF_TABLE.get(c, c) for c in text
            ).replace("\u3000", " ")

        # 6. 中文标点
        if self.cn_punct:
            text = "".join(_CN_PUNCT.get(c, c) for c in text)

        # 7. 合并空白
        if self.collapse_spaces:
            text = _MULTI_SPACE_RE.sub(" ", text)
            text = _MULTI_NEWLINE_RE.sub("\n\n", text)

        return PreprocessResult(
            text=text.strip(),
            removed_html=removed_html,
            removed_controls=removed_controls,
            removed_urls=removed_urls,
            removed_emails=removed_emails,
            removed_phones=removed_phones,
            original_length=original_length,
            cleaned_length=len(text.strip()),
        )

    def process_dict(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """对 dict 中所有 string 字段递归执行 process

        不修改非字符串值（保留 list / dict 整体结构）。
        """
        if not isinstance(payload, dict):
            return payload
        out: Dict[str, Any] = {}
        for k, v in payload.items():
            if isinstance(v, str):
                out[k] = self.process(v).text
            elif isinstance(v, dict):
                out[k] = self.process_dict(v)
            elif isinstance(v, list):
                out[k] = [
                    self.process(item).text if isinstance(item, str) else item
                    for item in v
                ]
            else:
                out[k] = v
        return out


# ============================================================
# 便捷函数
# ============================================================
_default_preprocessor: Optional[TextPreprocessor] = None


def get_preprocessor() -> TextPreprocessor:
    """获取默认预处理器（单例）"""
    global _default_preprocessor
    if _default_preprocessor is None:
        _default_preprocessor = TextPreprocessor()
    return _default_preprocessor


def clean_text(text: str) -> str:
    """单行调用：返回清洗后文本"""
    return get_preprocessor().process(text).text


__all__ = [
    "TextPreprocessor",
    "PreprocessResult",
    "get_preprocessor",
    "clean_text",
]
