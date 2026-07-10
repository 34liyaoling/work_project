"""快速初始化数据库 - 命令行使用"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from backend.storage.db import DatabaseManager, DB_PATH


def main():
    print(f"SQLite数据库路径: {DB_PATH}")
    db = DatabaseManager()
    db.init_db()
    print("数据库表结构初始化完成！")
    print(f"  简历表 (resumes)")
    print(f"  岗位表 (jobs)")
    print(f"  分析记录表 (analysis_records)")
    print(f"  审核队列表 (audit_queue)")

    stats = db.get_db_stats()
    print(f"\n当前数据统计:")
    print(f"  简历数: {stats.get('resume_count', 0)}")
    print(f"  岗位数: {stats.get('job_count', 0)}")
    print(f"  分析记录: {stats.get('analysis_count', 0)}")
    print(f"  待审核: {stats.get('pending_audit_count', 0)}")
    print(f"  数据库大小: {stats.get('db_size_bytes', 0) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
