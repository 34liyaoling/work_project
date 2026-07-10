"""数据处理管道 - 多源数据的标准化、清洗、转换"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime
from typing import Any
from models.job_model import JobPostSource, JobPostRaw

logger = logging.getLogger(__name__)


class DataPipeline:
    """数据处理管道：原始数据 → 清洗 → 标准化 → 输出"""

    # 数据源默认置信度
    SOURCE_CONFIDENCE = {
        JobPostSource.SAMPLE: 1.0,
        JobPostSource.MANUAL: 0.95,
        JobPostSource.REPORT: 0.90,
        JobPostSource.GITHUB: 0.75,
        JobPostSource.BOSS_ZHIPIN: 0.80,
        JobPostSource.LAGOU: 0.78,
        JobPostSource.LIEPIN: 0.76,
        JobPostSource.ZHAOPIN: 0.74,
        JobPostSource.WEB_SEARCH: 0.60,
    }

    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed")
        os.makedirs(self.data_dir, exist_ok=True)
        self.processing_stats = {
            "total_input": 0,
            "processed": 0,
            "filtered": 0,
            "errors": 0,
        }

    def process_raw_data(self, raw_item: dict, source: JobPostSource) -> JobPostRaw:
        """处理单条原始数据"""
        self.processing_stats["total_input"] += 1

        try:
            # 基础字段提取
            processed = JobPostRaw(
                source=source,
                source_confidence=self.SOURCE_CONFIDENCE.get(source, 0.7),
                timestamp=datetime.now(),
                raw_content=json.dumps(raw_item, ensure_ascii=False),
            )

            # 提取结构化字段（根据不同源可能有不同字段名）
            self._extract_fields(processed, raw_item)

            # 计算质量指标
            processed.completeness_score = self._calculate_completeness(processed)
            processed.freshness_score = self._calculate_freshness(processed)

            # 数据清洗
            self._clean_data(processed)

            self.processing_stats["processed"] += 1
            return processed

        except Exception as e:
            logger.error(f"数据处理失败: {e}")
            self.processing_stats["errors"] += 1
            raise

    def process_batch(self, raw_items: list[dict], source: JobPostSource) -> list[JobPostRaw]:
        """批量处理数据"""
        results = []
        for item in raw_items:
            try:
                processed = self.process_raw_data(item, source)
                results.append(processed)
            except Exception as e:
                logger.debug(f"跳过异常数据: {e}")
                self.processing_stats["filtered"] += 1
        return results

    def _extract_fields(self, processed: JobPostRaw, raw: dict):
        """从原始数据中提取结构化字段"""
        field_mappings = {
            "job_title": ["jobTitle", "title", "positionName", "job_name", "position", "job_title"],
            "company_name": ["companyName", "company", "brandName", "company_name"],
            "salary_min": ["salaryMin", "minSalary", "salary_low", "salary_min"],
            "salary_max": ["salaryMax", "maxSalary", "salary_high", "salary_max"],
            "location": ["city", "location", "workCity", "area"],
            "experience_min": ["experienceMin", "minExperience", "workYearMin"],
            "experience_max": ["experienceMax", "maxExperience", "workYearMax"],
            "education": ["education", "degree", "jobEducation", "educationLevel"],
            "industry": ["industry", "industryField", "industries"],
            "company_size": ["companySize", "scale", "employeeCount"],
            "job_description": ["jobDescription", "description", "detail", "job_content", "jd", "job_description"],
        }

        for target_field, source_keys in field_mappings.items():
            value = None
            for key in source_keys:
                if key in raw and raw[key]:
                    value = raw[key]
                    break

            if value is not None:
                setattr(processed, target_field, value)

        # 提取技能（可能在多个字段中）
        skills = self._extract_skills_from_raw(raw)
        if skills:
            processed.skills = skills

    def _extract_skills_from_raw(self, raw: dict) -> list[str]:
        """从原始数据中提取技能列表"""
        skills = []

        # 直接的skills字段
        for key in ["skills", "tags", "labels", "skillList"]:
            if key in raw and raw[key]:
                if isinstance(raw[key], list):
                    skills.extend(raw[key])
                elif isinstance(raw[key], str):
                    skills.extend([s.strip() for s in raw[key].split(",") if s.strip()])

        # 从JD文本中提取已知技能
        jd_text = ""
        for key in ["jobDescription", "description", "detail"]:
            if key in raw and raw[key]:
                jd_text += str(raw[key]) + " "

        if jd_text:
            from models.skill_taxonomy import get_all_skills
            known_skills = get_all_skills()
            for skill in known_skills:
                if skill.lower() in jd_text.lower() and skill not in skills:
                    skills.append(skill)

        return skills

    def _calculate_completeness(self, processed: JobPostRaw) -> float:
        """计算数据完整度分数(0-1)"""
        important_fields = [
            processed.job_title, processed.company_name,
            processed.skills, processed.salary_min, processed.location,
            processed.experience_min, processed.education
        ]
        filled = sum(1 for f in important_fields if f)
        return round(filled / len(important_fields), 2)

    def _calculate_freshness(self, processed: JobPostRaw) -> float:
        """计算数据新鲜度分数(0-1)"""
        # 简单实现：基于时间戳，越新鲜越高
        age_hours = (datetime.now() - processed.timestamp).total_seconds() / 3600
        freshness = max(0, 1 - age_hours / (24 * 30))  # 30天内线性衰减
        return round(freshness, 2)

    def _clean_data(self, processed: JobPostRaw):
        """数据清洗"""
        # 清理字符串字段
        string_fields = ['job_title', 'company_name', 'location', 'industry', 'education']
        for field in string_fields:
            val = getattr(processed, field, None)
            if isinstance(val, str):
                cleaned = re.sub(r'\s+', ' ', val.strip())
                setattr(processed, field, cleaned)

        # 清理薪资字段
        for field in ['salary_min', 'salary_max']:
            val = getattr(processed, field, None)
            if val is not None:
                try:
                    setattr(processed, field, int(val))
                except (ValueError, TypeError):
                    setattr(processed, field, None)

        # 去重技能
        if processed.skills:
            seen = set()
            unique_skills = []
            for s in processed.skills:
                s_clean = s.strip().lower()
                if s_clean and s_clean not in seen:
                    seen.add(s_clean)
                    unique_skills.append(s.strip())
            processed.skills = unique_skills

    def compute_record_hash(self, data: dict) -> str:
        """计算记录哈希值（用于去重）"""
        content = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(content.encode()).hexdigest()

    def deduplicate(self, records: list[JobPostRaw], threshold: float = 0.85) -> list[JobPostRaw]:
        """基于标题相似度的去重"""
        unique_records = []
        seen_titles = set()

        for record in records:
            title = (record.job_title or "").lower().strip()
            if not title:
                continue

            # 精确匹配
            if title in seen_titles:
                continue

            # 模糊匹配（简单版本：检查是否为子串）
            is_duplicate = False
            for seen in seen_titles:
                if title in seen or seen in title:
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_titles.add(title)
                unique_records.append(record)

        self.save_to_disk(unique_records, "deduplicated")
        return unique_records

    def get_stats(self) -> dict:
        """获取处理统计"""
        return self.processing_stats.copy()

    def save_to_disk(self, records, source_name="collected"):
        """将数据持久化到磁盘"""
        if not records:
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source_name}_{timestamp}.json"
        filepath = os.path.join(self.data_dir, filename)

        data = {
            "source": source_name,
            "timestamp": datetime.now().isoformat(),
            "count": len(records),
            "records": [r.model_dump() if hasattr(r, 'model_dump') else r for r in records],
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"数据已保存到 {filepath} ({len(records)} 条)")
        return filepath

    def load_from_disk(self, source_name=None):
        """从磁盘加载数据"""
        if not os.path.exists(self.data_dir):
            return []

        files = sorted(
            [f for f in os.listdir(self.data_dir) if f.endswith('.json')],
            reverse=True
        )

        if source_name:
            files = [f for f in files if f.startswith(source_name)]

        all_records = []
        for fname in files[:10]:  # 最多加载最近10个文件
            filepath = os.path.join(self.data_dir, fname)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_records.extend(data.get("records", []))
            except Exception as e:
                logger.warning(f"加载文件失败 {fname}: {e}")

        logger.info(f"从磁盘加载 {len(all_records)} 条记录 ({len(files)} 个文件)")
        return all_records

    def clean_job_data(self, raw_job: dict) -> dict:
        """
        清洗单条岗位数据（用于外部导入的原始数据）
        
        Args:
            raw_job: 原始岗位数据字典
            
        Returns:
            清洗后的岗位数据字典
        """
        cleaned = {}
        
        # 清洗岗位标题
        title = raw_job.get("job_title", "")
        if title:
            # 去除HTML标签
            title = re.sub(r'<[^>]+>', '', str(title))
            # 去除多余空白
            title = re.sub(r'\s+', ' ', title).strip()
            # 截断
            cleaned["job_title"] = title[:100]
        else:
            cleaned["job_title"] = ""
        
        # 清洗公司名
        company = raw_job.get("company_name", "")
        if company:
            company = re.sub(r'<[^>]+>', '', str(company))
            company = re.sub(r'\s+', ' ', company).strip()
            cleaned["company_name"] = company[:100]
        else:
            cleaned["company_name"] = ""
        
        # 清洗薪资
        for field in ["salary_min", "salary_max"]:
            val = raw_job.get(field)
            if val is not None:
                try:
                    # 提取数字
                    if isinstance(val, str):
                        match = re.search(r'(\d+(?:\.\d+)?)', val)
                        val = float(match.group(1)) if match else None
                    cleaned[field] = int(val) if val else None
                except (ValueError, TypeError):
                    cleaned[field] = None
            else:
                cleaned[field] = None
        
        # 清洗地点
        location = raw_job.get("location", "")
        if location:
            location = re.sub(r'<[^>]+>', '', str(location))
            location = re.sub(r'\s+', ' ', location).strip()
            cleaned["location"] = location[:50]
        else:
            cleaned["location"] = ""
        
        # 清洗技能列表
        skills = raw_job.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        elif isinstance(skills, list):
            skills = [str(s).strip() for s in skills if s]
        else:
            skills = []
        # 去重
        cleaned["skills"] = list(dict.fromkeys(skills))[:20]
        
        # 清洗岗位描述
        desc = raw_job.get("job_description", "")
        if desc:
            desc = re.sub(r'<[^>]+>', '', str(desc))
            desc = re.sub(r'\s+', ' ', desc).strip()
            cleaned["job_description"] = desc[:2000]
        else:
            cleaned["job_description"] = ""
        
        # 保留来源信息
        cleaned["source"] = raw_job.get("source", "external_collector")
        cleaned["source_url"] = raw_job.get("source_url", "")
        
        return cleaned

    def deduplicate_jobs(self, jobs: list[dict]) -> list[dict]:
        """
        对岗位列表进行去重
        
        Args:
            jobs: 岗位数据列表
            
        Returns:
            去重后的岗位列表
        """
        if not jobs:
            return []
        
        unique_jobs = []
        seen_keys = set()
        
        for job in jobs:
            # 使用标题前30字符作为去重key
            title = job.get("job_title", "")[:30].lower().strip()
            if not title:
                continue
            
            # 计算hash
            key = hashlib.md5(title.encode()).hexdigest()
            
            if key not in seen_keys:
                seen_keys.add(key)
                unique_jobs.append(job)
        
        logger.info(f"去重完成: {len(jobs)} -> {len(unique_jobs)}")
        return unique_jobs
