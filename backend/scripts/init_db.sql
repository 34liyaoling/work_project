-- =============================================================
-- CompetencyGraph MySQL 初始化脚本
-- 数据库：competency_graph
-- 字符集：utf8mb4
-- =============================================================

CREATE DATABASE IF NOT EXISTS `competency_graph`
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE `competency_graph`;

-- -------------------------------------------------------------
-- 1. JD 原始数据表
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `jd_records` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `jd_id` VARCHAR(64) NOT NULL COMMENT 'JD 唯一标识',
    `source` VARCHAR(32) COMMENT '数据来源：拉勾/Boss直聘/猎聘/LinkedIn',
    `source_url` VARCHAR(512) COMMENT '原始 URL',
    `company` VARCHAR(128) COMMENT '公司名',
    `title` VARCHAR(256) COMMENT '岗位名称',
    `category` VARCHAR(64) COMMENT '岗位类别',
    `level` VARCHAR(32) COMMENT '级别：初级/中级/高级/资深',
    `location` VARCHAR(64) COMMENT '工作地点',
    `salary_range` VARCHAR(64) COMMENT '薪资范围',
    `raw_text` TEXT COMMENT 'JD 原始文本',
    `parsed_data` JSON COMMENT 'LLM 解析结构化数据',
    `skills` JSON COMMENT '提取的技能列表',
    `published_at` DATETIME COMMENT 'JD 发布时间',
    `crawled_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '采集时间',
    `simhash` VARCHAR(64) COMMENT 'SimHash 指纹',
    `credibility_score` FLOAT DEFAULT 0.5 COMMENT '数据可信度 0-1',
    `is_processed` TINYINT DEFAULT 0 COMMENT '是否已处理 0/1',
    `is_duplicate` TINYINT DEFAULT 0 COMMENT '是否重复 0/1',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_jd_id` (`jd_id`),
    KEY `idx_source` (`source`),
    KEY `idx_company` (`company`),
    KEY `idx_category` (`category`),
    KEY `idx_simhash` (`simhash`),
    KEY `idx_source_published` (`source`, `published_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='招聘 JD 记录';

-- -------------------------------------------------------------
-- 2. 技能同义词
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `skill_synonyms` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `alias` VARCHAR(128) NOT NULL COMMENT '别名/缩写',
    `standard_name` VARCHAR(128) NOT NULL COMMENT '标准名称',
    `category` VARCHAR(64) COMMENT '技能分类',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_alias` (`alias`),
    KEY `idx_standard` (`standard_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='技能同义词映射';

-- -------------------------------------------------------------
-- 3. 采集日志
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `data_crawl_logs` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `source` VARCHAR(32) NOT NULL,
    `task_type` VARCHAR(32) COMMENT '任务类型: full/incremental',
    `started_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `finished_at` DATETIME NULL,
    `total_count` INT DEFAULT 0,
    `success_count` INT DEFAULT 0,
    `failed_count` INT DEFAULT 0,
    `error_message` TEXT NULL,
    `status` VARCHAR(16) DEFAULT 'running' COMMENT 'running/success/failed',
    PRIMARY KEY (`id`),
    KEY `idx_source` (`source`),
    KEY `idx_started_at` (`started_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据采集日志';

-- -------------------------------------------------------------
-- 4. 简历记录
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `resume_records` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `resume_id` VARCHAR(64) NOT NULL,
    `file_name` VARCHAR(256),
    `file_type` VARCHAR(16) COMMENT 'pdf/docx',
    `file_size` INT,
    `file_path` VARCHAR(512),
    `raw_text` TEXT,
    `parsed_data` JSON,
    `name` VARCHAR(64),
    `education` JSON,
    `work_experience` JSON,
    `projects` JSON,
    `skills` JSON,
    `skill_vector` JSON,
    `uploaded_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `parsed_at` DATETIME NULL,
    `parse_status` VARCHAR(16) DEFAULT 'pending' COMMENT 'pending/parsing/success/failed',
    `parse_accuracy` FLOAT,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_resume_id` (`resume_id`),
    KEY `idx_name` (`name`),
    KEY `idx_parse_status` (`parse_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历记录';

-- -------------------------------------------------------------
-- 5. 匹配记录
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `match_records` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `resume_id` VARCHAR(64) NOT NULL,
    `target_id` VARCHAR(64) NOT NULL COMMENT 'JD ID 或岗位方向 ID',
    `target_type` VARCHAR(16) COMMENT 'jd / role',
    `overall_score` FLOAT,
    `required_score` FLOAT,
    `preferred_score` FLOAT,
    `depth_score` FLOAT,
    `domain_score` FLOAT,
    `breakdown` JSON,
    `gap_skills` JSON,
    `recommendations` JSON,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_resume_id` (`resume_id`),
    KEY `idx_target_id` (`target_id`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人岗匹配记录';

-- -------------------------------------------------------------
-- 6. 岗位定义卡片
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `job_role_cards` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `role_id` VARCHAR(64) NOT NULL,
    `name` VARCHAR(128),
    `category` VARCHAR(64),
    `level` VARCHAR(32),
    `core_responsibilities` JSON,
    `required_skills` JSON,
    `preferred_skills` JSON,
    `typical_scenarios` JSON,
    `confidence` FLOAT,
    `evidence_sources` JSON,
    `is_new` TINYINT DEFAULT 0,
    `is_reviewed` TINYINT DEFAULT 0,
    `reviewed_by` VARCHAR(64) NULL,
    `reviewed_at` DATETIME NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_role_id` (`role_id`),
    KEY `idx_category` (`category`),
    KEY `idx_is_new` (`is_new`),
    KEY `idx_is_reviewed` (`is_reviewed`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='岗位定义卡片';

-- -------------------------------------------------------------
-- 7. 图谱变更日志
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `graph_change_logs` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `change_type` VARCHAR(16) COMMENT 'added/removed/modified/weight_changed',
    `node_type` VARCHAR(32) COMMENT 'jobrole/skill/tool',
    `node_id` VARCHAR(64),
    `node_name` VARCHAR(128),
    `change_detail` JSON,
    `confidence` FLOAT,
    `source_count` INT DEFAULT 1,
    `is_auto_applied` TINYINT DEFAULT 0,
    `snapshot_id` VARCHAR(64) NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_change_type` (`change_type`),
    KEY `idx_node_id` (`node_id`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='图谱变更日志';

-- -------------------------------------------------------------
-- 8. 图谱快照
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `graph_snapshots` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `snapshot_id` VARCHAR(64) NOT NULL,
    `description` VARCHAR(256),
    `node_count` INT DEFAULT 0,
    `edge_count` INT DEFAULT 0,
    `snapshot_data` JSON,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_snapshot_id` (`snapshot_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='图谱版本快照';

-- -------------------------------------------------------------
-- 9. 人工审核日志
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `audit_logs` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `entity_type` VARCHAR(32) COMMENT 'jobrole/skill/edge',
    `entity_id` VARCHAR(64),
    `entity_data` JSON,
    `reason` VARCHAR(256),
    `status` VARCHAR(16) DEFAULT 'pending' COMMENT 'pending/approved/rejected',
    `reviewed_by` VARCHAR(64) NULL,
    `reviewed_at` DATETIME NULL,
    `review_comment` TEXT NULL,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_entity_id` (`entity_id`),
    KEY `idx_status` (`status`),
    KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人工审核日志';

-- =============================================================
-- 完成
-- =============================================================
