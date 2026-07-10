"""SQLite持久化存储层 - DatabaseManager"""

import json
import logging
import sqlite3
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
DB_PATH = os.path.join(DB_DIR, "kg_system.db")


class DatabaseManager:
    """SQLite数据库管理器，提供简历/岗位/审核等数据的持久化存储"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_db_dir()

    def _ensure_db_dir(self):
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_db(self):
        """创建表结构"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS resumes (
                    resume_id TEXT PRIMARY KEY,
                    profile_data TEXT NOT NULL,
                    name TEXT,
                    skill_count INTEGER DEFAULT 0,
                    technical_level TEXT DEFAULT 'mid',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_data TEXT NOT NULL,
                    title TEXT,
                    domain TEXT,
                    source TEXT DEFAULT 'manual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS analysis_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_type TEXT NOT NULL,
                    record_data TEXT NOT NULL,
                    resume_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS audit_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT NOT NULL,
                    item_data TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    reviewer_note TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_domain ON jobs(domain);
                CREATE INDEX IF NOT EXISTS idx_analysis_resume ON analysis_records(resume_id);
                CREATE INDEX IF NOT EXISTS idx_audit_status ON audit_queue(status);

                -- Agent记忆持久化表
                CREATE TABLE IF NOT EXISTS agent_long_term_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    decision TEXT,
                    outcome TEXT,
                    success INTEGER DEFAULT 0,
                    lesson TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS agent_entity_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    entity_type TEXT,
                    attrs TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(agent_name, entity_id)
                );

                CREATE INDEX IF NOT EXISTS idx_agent_memory_agent ON agent_long_term_memory(agent_name);
                CREATE INDEX IF NOT EXISTS idx_agent_memory_task ON agent_long_term_memory(task_type);
                CREATE INDEX IF NOT EXISTS idx_agent_entity_agent ON agent_entity_memory(agent_name);
            """)

            conn.commit()
            logger.info("数据库表结构初始化完成")
        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
            raise
        finally:
            conn.close()

    def save_resume(self, resume_id: str, profile_data: dict):
        """保存/更新简历画像"""
        try:
            conn = self._get_conn()
            profile_json = json.dumps(profile_data, ensure_ascii=False, default=str)
            name = profile_data.get("name", "")
            skills = profile_data.get("skills_with_credibility", [])
            skill_count = len(skills)
            technical_level = profile_data.get("overall_technical_level", "mid")

            conn.execute("""
                INSERT INTO resumes (resume_id, profile_data, name, skill_count, technical_level, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(resume_id) DO UPDATE SET
                    profile_data = excluded.profile_data,
                    name = excluded.name,
                    skill_count = excluded.skill_count,
                    technical_level = excluded.technical_level,
                    updated_at = CURRENT_TIMESTAMP
            """, (resume_id, profile_json, name, skill_count, technical_level))
            conn.commit()
            logger.info(f"简历已保存: {resume_id}")
        except Exception as e:
            logger.error(f"保存简历失败 [{resume_id}]: {e}")
            raise
        finally:
            conn.close()

    def get_resume(self, resume_id: str) -> Optional[dict]:
        """获取简历画像"""
        try:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT profile_data FROM resumes WHERE resume_id = ?",
                (resume_id,)
            ).fetchone()
            if row:
                return json.loads(row["profile_data"])
            return None
        except Exception as e:
            logger.error(f"获取简历失败 [{resume_id}]: {e}")
            return None
        finally:
            conn.close()

    def list_resumes(self, limit: int = 50) -> list[dict]:
        """列出所有简历"""
        try:
            conn = self._get_conn()
            rows = conn.execute("""
                SELECT resume_id, name, skill_count, technical_level, created_at, updated_at
                FROM resumes ORDER BY updated_at DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"列出简历失败: {e}")
            return []
        finally:
            conn.close()

    def delete_resume(self, resume_id: str) -> bool:
        """删除简历"""
        try:
            conn = self._get_conn()
            cursor = conn.execute("DELETE FROM resumes WHERE resume_id = ?", (resume_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"简历已删除: {resume_id}")
            return deleted
        except Exception as e:
            logger.error(f"删除简历失败 [{resume_id}]: {e}")
            return False
        finally:
            conn.close()

    def save_job(self, job_data: dict):
        """保存岗位数据"""
        try:
            conn = self._get_conn()
            job_json = json.dumps(job_data, ensure_ascii=False, default=str)
            title = job_data.get("title", "") or job_data.get("job_title", "")
            domain = job_data.get("domain", "")
            source = job_data.get("source", "manual")

            conn.execute("""
                INSERT INTO jobs (job_data, title, domain, source)
                VALUES (?, ?, ?, ?)
            """, (job_json, title, domain, source))
            conn.commit()
            logger.info(f"岗位已保存: {title}")
        except Exception as e:
            logger.error(f"保存岗位失败: {e}")
            raise
        finally:
            conn.close()

    def get_jobs(self, domain: Optional[str] = None, limit: int = 100) -> list[dict]:
        """获取岗位列表"""
        try:
            conn = self._get_conn()
            if domain:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE domain = ? ORDER BY created_at DESC LIMIT ?",
                    (domain, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            result = []
            for r in rows:
                item = dict(r)
                item["job_data"] = json.loads(item["job_data"])
                result.append(item)
            return result
        except Exception as e:
            logger.error(f"获取岗位列表失败: {e}")
            return []
        finally:
            conn.close()

    def add_audit_item(self, item: dict):
        """添加审核项"""
        try:
            conn = self._get_conn()
            item_json = json.dumps(item, ensure_ascii=False, default=str)
            item_type = item.get("item_type", "general")

            conn.execute("""
                INSERT INTO audit_queue (item_type, item_data)
                VALUES (?, ?)
            """, (item_type, item_json))
            conn.commit()
            logger.info(f"审核项已添加: {item_type}")
        except Exception as e:
            logger.error(f"添加审核项失败: {e}")
            raise
        finally:
            conn.close()

    def get_audit_queue(self, status: str = "pending") -> list[dict]:
        """获取审核队列"""
        try:
            conn = self._get_conn()
            rows = conn.execute(
                "SELECT * FROM audit_queue WHERE status = ? ORDER BY created_at ASC",
                (status,)
            ).fetchall()
            result = []
            for r in rows:
                item = dict(r)
                item["item_data"] = json.loads(item["item_data"])
                result.append(item)
            return result
        except Exception as e:
            logger.error(f"获取审核队列失败: {e}")
            return []
        finally:
            conn.close()

    def update_audit_item(self, item_id: int, status: str, reviewer_note: str = ""):
        """更新审核状态"""
        try:
            conn = self._get_conn()
            conn.execute("""
                UPDATE audit_queue
                SET status = ?, reviewer_note = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, reviewer_note, item_id))
            conn.commit()
            logger.info(f"审核项已更新: id={item_id}, status={status}")
        except Exception as e:
            logger.error(f"更新审核项失败 [id={item_id}]: {e}")
            raise
        finally:
            conn.close()

    def get_db_stats(self) -> dict:
        """获取数据库统计信息"""
        try:
            conn = self._get_conn()
            stats = {}

            stats["resume_count"] = conn.execute(
                "SELECT COUNT(*) as cnt FROM resumes"
            ).fetchone()["cnt"]

            stats["job_count"] = conn.execute(
                "SELECT COUNT(*) as cnt FROM jobs"
            ).fetchone()["cnt"]

            stats["analysis_count"] = conn.execute(
                "SELECT COUNT(*) as cnt FROM analysis_records"
            ).fetchone()["cnt"]

            stats["pending_audit_count"] = conn.execute(
                "SELECT COUNT(*) as cnt FROM audit_queue WHERE status = 'pending'"
            ).fetchone()["cnt"]

            stats["total_audit_count"] = conn.execute(
                "SELECT COUNT(*) as cnt FROM audit_queue"
            ).fetchone()["cnt"]

            stats["domain_distribution"] = {
                r["domain"]: r["cnt"]
                for r in conn.execute(
                    "SELECT domain, COUNT(*) as cnt FROM jobs WHERE domain != '' GROUP BY domain ORDER BY cnt DESC"
                ).fetchall()
            }

            stats["db_size_bytes"] = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

            return stats
        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {"error": str(e)}
        finally:
            conn.close()

    # ==================== Agent记忆持久化 ====================

    def save_agent_experience(self, agent_name: str, task_type: str,
                              decision: str, outcome: str, success: bool,
                              lesson: str = "") -> int:
        """保存Agent长期记忆（经验）"""
        try:
            conn = self._get_conn()
            cursor = conn.execute("""
                INSERT INTO agent_long_term_memory
                    (agent_name, task_type, decision, outcome, success, lesson)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (agent_name, task_type, decision[:500], outcome[:1000],
                  1 if success else 0, lesson[:500]))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"保存Agent经验失败: {e}")
            return 0
        finally:
            conn.close()

    def get_agent_experiences(self, agent_name: str, task_type: str = None,
                              limit: int = 50, only_success: bool = False) -> list[dict]:
        """获取Agent历史经验"""
        try:
            conn = self._get_conn()
            query = "SELECT * FROM agent_long_term_memory WHERE agent_name = ?"
            params = [agent_name]
            if task_type:
                query += " AND task_type = ?"
                params.append(task_type)
            if only_success:
                query += " AND success = 1"
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"获取Agent经验失败: {e}")
            return []
        finally:
            conn.close()

    def track_agent_entity(self, agent_name: str, entity_id: str,
                           entity_type: str, attrs: dict):
        """跟踪Agent实体变化（首次创建或更新）"""
        try:
            conn = self._get_conn()
            attrs_json = json.dumps(attrs, ensure_ascii=False, default=str)
            conn.execute("""
                INSERT INTO agent_entity_memory (agent_name, entity_id, entity_type, attrs, first_seen, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(agent_name, entity_id) DO UPDATE SET
                    attrs = excluded.attrs,
                    updated_at = CURRENT_TIMESTAMP
            """, (agent_name, entity_id, entity_type, attrs_json))
            conn.commit()
        except Exception as e:
            logger.error(f"跟踪Agent实体失败: {e}")
        finally:
            conn.close()

    def get_agent_entity_history(self, agent_name: str, entity_id: str) -> Optional[dict]:
        """获取Agent跟踪实体的历史"""
        try:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT * FROM agent_entity_memory WHERE agent_name = ? AND entity_id = ?",
                (agent_name, entity_id)
            ).fetchone()
            if row:
                result = dict(row)
                if result.get("attrs"):
                    result["attrs"] = json.loads(result["attrs"])
                return result
            return None
        except Exception as e:
            logger.error(f"获取Agent实体历史失败: {e}")
            return None
        finally:
            conn.close()

    def get_agent_memory_stats(self) -> dict:
        """获取Agent记忆统计"""
        try:
            conn = self._get_conn()
            stats = {}

            stats["total_experiences"] = conn.execute(
                "SELECT COUNT(*) as cnt FROM agent_long_term_memory"
            ).fetchone()["cnt"]

            stats["success_experiences"] = conn.execute(
                "SELECT COUNT(*) as cnt FROM agent_long_term_memory WHERE success = 1"
            ).fetchone()["cnt"]

            stats["tracked_entities"] = conn.execute(
                "SELECT COUNT(*) as cnt FROM agent_entity_memory"
            ).fetchone()["cnt"]

            stats["by_agent"] = {
                r["agent_name"]: r["cnt"]
                for r in conn.execute(
                    "SELECT agent_name, COUNT(*) as cnt FROM agent_long_term_memory GROUP BY agent_name ORDER BY cnt DESC"
                ).fetchall()
            }

            return stats
        except Exception as e:
            logger.error(f"获取Agent记忆统计失败: {e}")
            return {"error": str(e)}
        finally:
            conn.close()


# 全局单例
_db_instance: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """获取DatabaseManager单例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
        _db_instance.init_db()
    return _db_instance
