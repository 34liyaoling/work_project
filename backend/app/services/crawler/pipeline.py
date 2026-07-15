"""Scrapy-style 数据管道

提供：
* :class:`PipelineContext` - 管道执行上下文（批次级状态）
* :class:`CrawlPipeline`   - 顺序执行的中间件链
* 内置中间件：
    - 去重（基于 jd_id / SimHash）
    - 基础清洗（trim / 去空）
    - 入库（写 ES / MySQL，可选）
    - 本地 JSONL 落盘（默认开启，便于离线调试）

设计原则：
    1. 框架无关（不依赖 Scrapy），通过生成器串联
    2. 单个中间件失败不阻塞整体（隔离 try/except）
    3. 上下文携带本批次元数据（来源、数量、去重统计）
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Iterable, List, Optional

from app.core.logger import log
from app.services.crawler.base import JDItem


# 类型：中间件签名
Middleware = Callable[["PipelineContext", List[JDItem]], Awaitable[List[JDItem]]]


@dataclass
class PipelineContext:
    """管道上下文：单次 crawl 调用的全部状态"""

    source: str
    keyword: str = ""
    pages: int = 1
    started_at: float = field(default_factory=time.time)
    stats: Dict[str, Any] = field(default_factory=lambda: defaultdict(int))
    errors: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)

    def log_summary(self) -> None:
        log.info(
            f"[Pipeline] source={self.source} keyword={self.keyword} "
            f"stats={dict(self.stats)} errors={len(self.errors)}"
        )


# ============================================================
# 内置中间件
# ============================================================
async def dedup_middleware(ctx: PipelineContext, items: List[JDItem]) -> List[JDItem]:
    """基于 jd_id 的内存去重（同一批次内）"""
    seen: set = set()
    out: List[JDItem] = []
    for it in items:
        if it.jd_id in seen:
            ctx.stats["dup_jd_id"] += 1
            continue
        seen.add(it.jd_id)
        out.append(it)
    ctx.stats["after_dedup"] = len(out)
    return out


async def basic_clean_middleware(ctx: PipelineContext, items: List[JDItem]) -> List[JDItem]:
    """基础清洗：去空 / 去多余空白 / 截断超长文本"""
    cleaned: List[JDItem] = []
    for it in items:
        if not it.raw_text and not it.title:
            ctx.stats["empty_skipped"] += 1
            continue
        # 截断
        if len(it.raw_text) > 8000:
            it.raw_text = it.raw_text[:8000]
        # 标准化空白
        it.raw_text = " ".join(it.raw_text.split())
        if it.title:
            it.title = " ".join(it.title.split())[:256]
        if it.company:
            it.company = " ".join(it.company.split())[:128]
        cleaned.append(it)
    ctx.stats["after_clean"] = len(cleaned)
    return cleaned


async def write_jsonl_middleware(
    ctx: PipelineContext,
    items: List[JDItem],
    output_dir: str = "./data/raw",
) -> List[JDItem]:
    """把本批次结果以 JSONL 格式追加到 ``data/raw/{source}_{ts}.jsonl``"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        ts = int(time.time())
        path = os.path.join(output_dir, f"{ctx.source}_{ts}.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it.to_dict(), ensure_ascii=False) + "\n")
        ctx.stats["wrote_jsonl"] = path
    except Exception as e:  # noqa: BLE001
        log.error(f"write_jsonl_middleware 失败: {e}")
        ctx.errors.append(f"jsonl:{e}")
    return items


async def write_es_middleware(
    ctx: PipelineContext,
    items: List[JDItem],
    es_client: Optional[Any] = None,
    index_name: str = "jd_index",
) -> List[JDItem]:
    """写入 Elasticsearch（可选；es_client 不可用时跳过）"""
    if es_client is None:
        from app.core.es_client import es_client
        es_client = es_client.client
    if es_client is None:
        log.debug("ES 不可用，跳过入库")
        return items
    try:
        for it in items:
            es_client.index(
                index=index_name,
                id=it.jd_id,
                document=it.to_dict(),
            )
        ctx.stats["es_indexed"] = len(items)
    except Exception as e:  # noqa: BLE001
        log.error(f"write_es_middleware 失败: {e}")
        ctx.errors.append(f"es:{e}")
    return items


async def write_mysql_middleware(
    ctx: PipelineContext,
    items: List[JDItem],
    db_session_factory: Optional[Callable] = None,
) -> List[JDItem]:
    """写入 MySQL（可选；db_session_factory 未提供时跳过）"""
    if db_session_factory is None:
        log.debug("db_session_factory 未提供，跳过 MySQL 写入")
        return items
    try:
        session = db_session_factory()
        try:
            from app.models.jd import JDRecord  # 局部导入避免循环
            for it in items:
                rec = JDRecord(
                    jd_id=it.jd_id,
                    source=it.source,
                    source_url=it.source_url,
                    company=it.company,
                    title=it.title,
                    category=it.category,
                    level=it.level,
                    location=it.location,
                    salary_range=it.salary_range,
                    raw_text=it.raw_text,
                    skills=it.skills,
                )
                session.merge(rec)
            session.commit()
            ctx.stats["mysql_upserted"] = len(items)
        finally:
            session.close()
    except Exception as e:  # noqa: BLE001
        log.error(f"write_mysql_middleware 失败: {e}")
        ctx.errors.append(f"mysql:{e}")
    return items


# ============================================================
# CrawlPipeline
# ============================================================
class CrawlPipeline:
    """爬虫管道：把若干中间件串联，按顺序处理 JDItem 列表"""

    def __init__(self, middlewares: Optional[List[Middleware]] = None) -> None:
        self.middlewares: List[Middleware] = middlewares or [
            dedup_middleware,
            basic_clean_middleware,
            write_jsonl_middleware,
        ]

    def use(self, mw: Middleware) -> "CrawlPipeline":
        """链式注册中间件"""
        self.middlewares.append(mw)
        return self

    async def process(
        self,
        source: str,
        items: List[JDItem],
        keyword: str = "",
        pages: int = 1,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[JDItem]:
        """执行整条管道"""
        ctx = PipelineContext(
            source=source,
            keyword=keyword,
            pages=pages,
            options=options or {},
        )
        ctx.stats["input"] = len(items)
        current = items
        for mw in self.middlewares:
            try:
                current = await mw(ctx, current)
            except Exception as e:  # noqa: BLE001
                log.error(f"中间件 {mw.__name__} 失败: {e}")
                ctx.errors.append(f"{mw.__name__}:{e}")
        ctx.stats["output"] = len(current)
        ctx.log_summary()
        return current

    async def process_stream(
        self,
        source: str,
        item_stream: AsyncIterator[JDItem],
        keyword: str = "",
        pages: int = 1,
    ) -> List[JDItem]:
        """从异步迭代器消费 JDItem 并跑管道"""
        items: List[JDItem] = []
        async for it in item_stream:
            items.append(it)
        return await self.process(source, items, keyword=keyword, pages=pages)


# ============================================================
# 工具：从本地 JSONL 读取（用于"样例数据回退"）
# ============================================================
def load_jsonl_samples(path: str) -> List[Dict[str, Any]]:
    """从 JSONL 文件读取样例数据，返回 dict 列表"""
    if not os.path.exists(path):
        log.warning(f"样例文件不存在: {path}")
        return []
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception as e:  # noqa: BLE001
                log.error(f"解析 {path} 一行失败: {e}")
    return out


__all__ = [
    "PipelineContext",
    "CrawlPipeline",
    "Middleware",
    "dedup_middleware",
    "basic_clean_middleware",
    "write_jsonl_middleware",
    "write_es_middleware",
    "write_mysql_middleware",
    "load_jsonl_samples",
]
