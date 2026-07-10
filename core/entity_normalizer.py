"""实体标准化器 - 技能名称标准化、同义词映射、格式统一"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# ===== 技能同义词映射表 =====
SKILL_SYNONYMS = {
    # === 编程语言 ===
    "python编程": "Python",
    "python开发": "Python",
    "python3": "Python",
    "python语言": "Python",
    "java编程": "Java",
    "java开发": "Java",
    "golang": "Go",
    "go语言": "Go",
    "golang编程": "Go",
    "javascript编程": "JavaScript",
    "js": "JavaScript",
    "typescript编程": "TypeScript",
    "ts": "TypeScript",
    "c++编程": "C++",
    "c/c++": "C++",
    "c语言": "C",
    "c#编程": "C#",
    "rust编程": "Rust",
    "kotlin编程": "Kotlin",
    "swift编程": "Swift",
    "scala编程": "Scala",
    "ruby编程": "Ruby",
    "php编程": "PHP",
    "shell编程": "Shell",
    "shell脚本": "Shell",
    "bash": "Shell",
    "sql编程": "SQL",
    "r语言": "R",
    
    # === 深度学习框架 ===
    "pytorch框架": "PyTorch",
    "pytorch": "PyTorch",
    "tensorflow框架": "TensorFlow",
    "tensorflow": "TensorFlow",
    "keras框架": "Keras",
    "paddlepaddle框架": "PaddlePaddle",
    "飞桨": "PaddlePaddle",
    "mxnet框架": "MXNet",
    "jax框架": "JAX",
    "caffe框架": "Caffe",
    
    # === 大模型技术 ===
    "transformer架构": "Transformer",
    "transformer模型": "Transformer",
    "bert模型": "BERT",
    "gpt模型": "GPT",
    "llm": "大语言模型",
    "大模型": "大语言模型",
    "大语言模型": "大语言模型",
    "langchain框架": "LangChain",
    "langchain": "LangChain",
    "rag技术": "RAG",
    "rag系统": "RAG",
    "rag系统设计": "RAG",
    "检索增强生成": "RAG",
    "prompt工程": "Prompt Engineering",
    "提示词工程": "Prompt Engineering",
    "prompt设计": "Prompt Engineering",
    "lora微调": "LoRA",
    "lora": "LoRA",
    "qlora": "QLoRA",
    "模型微调": "Fine-tuning",
    "finetune": "Fine-tuning",
    "fine-tuning": "Fine-tuning",
    "微调": "Fine-tuning",
    "rlhf": "RLHF",
    "dpo": "DPO",
    "模型蒸馏": "模型蒸馏",
    "思维链": "Chain-of-Thought",
    "chain-of-thought": "Chain-of-Thought",
    "function calling": "Function Calling",
    "函数调用": "Function Calling",
    "react模式": "ReAct模式",
    "多智能体": "多智能体协作",
    "多智能体系统": "多智能体协作",
    "autogpt": "AutoGPT",
    "babyagi": "BabyAGI",
    "crewai": "CrewAI",
    "autogen": "AutoGen",

    # === 容器与编排 ===
    "docker容器": "Docker",
    "docker技术": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "k8s运维": "Kubernetes",
    "容器编排": "Kubernetes",
    "containerd": "containerd",
    "podman": "Podman",

    # === 数据库 ===
    "mysql数据库": "MySQL",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "pg数据库": "PostgreSQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "redis缓存": "Redis",
    "redis": "Redis",
    "elasticsearch": "Elasticsearch",
    "es": "Elasticsearch",
    "elasticsearch搜索引擎": "Elasticsearch",
    "clickhouse": "ClickHouse",
    "hbase": "HBase",
    "cassandra": "Cassandra",
    "tidb": "TiDB",
    "starrocks": "StarRocks",
    "doris": "Doris",

    # === 数据处理 ===
    "apache spark": "Spark",
    "spark计算": "Spark",
    "spark": "Spark",
    "apache flink": "Flink",
    "flink计算": "Flink",
    "flink": "Flink",
    "hadoop": "Hadoop",
    "hadoop生态系统": "Hadoop",
    "hive数仓": "Hive",
    "kafka消息队列": "Kafka",
    "kafka": "Kafka",
    "apache kafka": "Kafka",
    "airflow调度": "Airflow",
    "airflow": "Airflow",
    "数据湖": "数据湖(Iceberg/Hudi/Delta Lake)",
    "数据湖iceberg": "数据湖(Iceberg/Hudi/Delta Lake)",
    "iceberg": "数据湖(Iceberg/Hudi/Delta Lake)",
    "hudi": "数据湖(Iceberg/Hudi/Delta Lake)",
    "delta lake": "数据湖(Iceberg/Hudi/Delta Lake)",

    # === 前端 ===
    "react框架": "React",
    "react.js": "React",
    "reactjs": "React",
    "vue框架": "Vue",
    "vue.js": "Vue",
    "vuejs": "Vue",
    "angular框架": "Angular",
    "angular.js": "Angular",
    "angularjs": "Angular",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "nuxtjs": "Nuxt.js",
    "nuxt.js": "Nuxt.js",
    "typescript前端": "TypeScript",
    "tailwind css": "TailwindCSS",
    "tailwindcss": "TailwindCSS",
    "webpack打包": "Webpack",
    "vite打包": "Vite",
    "微信小程序": "小程序开发",
    "小程序": "小程序开发",

    # === 后端 ===
    "spring boot": "Java/Spring Boot",
    "springboot": "Java/Spring Boot",
    "spring": "Java/Spring Boot",
    "django框架": "Python/FastAPI/Django/Flask",
    "flask框架": "Python/FastAPI/Django/Flask",
    "fastapi框架": "Python/FastAPI/Django/Flask",
    "gin框架": "Go/Gin",
    "express框架": "Node.js/Express/NestJS",
    "nestjs": "Node.js/Express/NestJS",
    "restful api": "API设计(RESTful/GraphQL/gRPC)",
    "rest api": "API设计(RESTful/GraphQL/gRPC)",
    "graphql": "API设计(RESTful/GraphQL/gRPC)",
    "grpc": "API设计(RESTful/GraphQL/gRPC)",

    # === 云计算 ===
    "aws云": "AWS",
    "aws服务": "AWS",
    "阿里云": "阿里云",
    "腾讯云": "腾讯云",
    "华为云": "华为云",
    "azure云": "Azure",
    "gcp": "GCP",
    "谷歌云": "GCP",
    "云原生": "云原生",
    "serverless": "Serverless",
    "无服务计算": "Serverless",

    # === DevOps ===
    "ci/cd": "CI/CD",
    "cICD": "CI/CD",
    "jenkins": "Jenkins",
    "gitlab ci": "GitLab CI",
    "gitlab-ci": "GitLab CI",
    "github actions": "GitHub Actions",
    "github-actions": "GitHub Actions",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "prometheus监控": "Prometheus",
    "prometheus": "Prometheus",
    "grafana": "Grafana",
    "elk": "ELK Stack",
    "elasticsearch日志": "ELK Stack",

    # === 移动端 ===
    "ios开发": "iOS(Swift/UIKit)",
    "swift开发": "iOS(Swift/UIKit)",
    "android开发": "Android(Kotlin/Jetpack)",
    "kotlin开发": "Android(Kotlin/Jetpack)",
    "flutter框架": "Flutter",
    "flutter": "Flutter",
    "react native": "React Native",
    "rn开发": "React Native",

    # === 安全 ===
    "网络安全": "网络安全",
    "信息安全": "信息安全",
    "渗透测试": "渗透测试",
    "渗透": "渗透测试",
    "漏洞挖掘": "漏洞挖掘",
    "逆向": "逆向工程",
    "逆向工程": "逆向工程",
    "web安全": "Web安全",
    "安全审计": "安全审计",
    "密码学": "密码学",
    "零信任": "零信任架构",

    # === 一般术语 ===
    "git版本控制": "Git",
    "git": "Git",
    "github": "Git",
    "linux操作系统": "Linux",
    "linux系统": "Linux",
    "dockercompose": "Docker Compose",
    "docker compose": "Docker Compose",
    "微服务": "微服务架构",
    "微服务设计": "微服务架构",
    "分布式": "分布式系统",
    "分布式系统": "分布式系统",
    "高并发": "高并发",
    "高并发设计": "高并发",
}


class EntityNormalizer:
    """实体标准化器 - 统一技能名称、映射同义词"""

    def __init__(self, llm_service=None, enable_llm_fallback: bool = True):
        self.synonyms = SKILL_SYNONYMS
        self.llm = llm_service
        self._normalize_cache = {}
        self._llm_inferrer = None
        # 延迟加载 LLM 推断器（避免循环依赖和启动时连接 LLM）
        if enable_llm_fallback:
            try:
                from core.llm_skill_inferrer import get_llm_skill_inferrer
                self._llm_inferrer = get_llm_skill_inferrer()
            except Exception as e:
                logger.debug(f"LLM推断器加载失败，仅使用硬编码: {e}")
                self._llm_inferrer = None

    def normalize(self, name: str) -> str:
        """标准化技能名称"""
        if not name or not isinstance(name, str):
            return ""
        
        name = name.strip()
        if not name:
            return ""
        
        # 缓存命中
        if name in self._normalize_cache:
            return self._normalize_cache[name]
        
        result = self._normalize(name)
        self._normalize_cache[name] = result
        return result

    def _normalize(self, name: str) -> str:
        """执行标准化（硬编码优先 → LLM兜底）"""
        original = name

        # 第1层：硬编码同义词映射
        name_lower = name.lower().strip()
        if name_lower in self.synonyms:
            return self.synonyms[name_lower]

        # 部分匹配：输入中包含已知技能名
        for key, value in self.synonyms.items():
            if key in name_lower or name_lower in key:
                return value

        # 第2层：规则标准化
        name = self._apply_rules(name)
        name = self._clean_name(name)

        # 第3层：LLM 兜底推断（仅当上面都没命中且 LLM 可用时）
        if name and self._llm_inferrer is not None:
            try:
                inferred = self._llm_inferrer.infer_synonym(name)
                if inferred and inferred != name:
                    return inferred
            except Exception as e:
                logger.debug(f"LLM同义词推断失败 [{name}]: {e}")

        return name

    def _apply_rules(self, name: str) -> str:
        """应用标准化规则"""
        name = name.strip()
        
        # 统一大小写（专有名词保留原样）
        known_uppercase = {
            "python", "java", "rust", "go", "kotlin", "swift", "dart",
            "pytorch", "tensorflow", "keras", "mxnet", "jax",
            "langchain", "llamaindex", "langgraph", "autogpt", "babyagi",
            "crewai", "autogen", "react", "vue", "angular", "flutter",
            "docker", "kubernetes", "k8s", "redis", "mysql", "mongodb",
            "postgresql", "elasticsearch", "clickhouse", "hbase",
            "spark", "flink", "hadoop", "hive", "kafka", "airflow",
            "terraform", "ansible", "jenkins", "prometheus", "grafana",
            "github", "gitlab", "nextjs", "nuxtjs", "nodejs",
            "fastapi", "django", "flask", "gin", "nestjs",
            "pytorch", "tensorflow", "keras", "paddlepaddle",
            "solidity", "vyper", "istio", "envoy", "linkerd",
            "terraform", "pulumi", "helm", "argocd", "tekton",
        }
        words = name.split()
        cleaned_words = []
        for w in words:
            w_clean = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff+#.-]', '', w)
            if w_clean:
                if w_clean.lower() in known_uppercase and not w_clean[0].isupper():
                    w_clean = known_uppercase_mapping().get(w_clean.lower(), w_clean.title())
                elif w_clean[0].isupper() and w_clean.lower() not in known_uppercase:
                    pass
                cleaned_words.append(w_clean)
        
        name = " ".join(cleaned_words)
        
        return name
    
    def _clean_name(self, name: str) -> str:
        """清理名称格式"""
        name = name.strip()
        name = re.sub(r'\s+', ' ', name)
        name = re.sub(r'[\"\'""]', '', name)
        name = name.strip('.,;:!?（）()【】[]《》<>')
        name = name.strip()
        return name

    def normalize_with_llm(self, name: str) -> str:
        """使用LLM兜底标准化"""
        if not self.llm:
            return self.normalize(name)
        
        try:
            prompt = f"""请将以下技能名称标准化为标准的技术技能名称。
规则：
1. 统一大小写：python → Python, pytorch → PyTorch
2. 去除冗余：python编程 → Python
3. 映射同义词：deep learning → 深度学习
4. 去除版本号：Python3 → Python
5. 保留复合词：Machine Learning → 机器学习

输入: {name}
输出: 只返回标准化后的名称"""
            
            result = self.llm.chat_completion([{"role": "user", "content": prompt}])
            if result:
                standardized = result.strip().strip('"\'')
                if standardized and standardized != name:
                    return standardized
        except Exception as e:
            logger.warning(f"LLM标准化失败 [{name}]: {e}")
        
        return self.normalize(name)

    def batch_normalize(self, names: list[str]) -> list[str]:
        """批量标准化"""
        return [self.normalize(n) for n in names]

    def is_standardized(self, name: str) -> bool:
        """检查名称是否已经是标准格式"""
        return self.normalize(name) == name


def known_uppercase_mapping() -> dict:
    """获取已知大写映射"""
    return {
        "python": "Python", "java": "Java", "rust": "Rust", "go": "Go",
        "kotlin": "Kotlin", "swift": "Swift", "dart": "Dart",
        "pytorch": "PyTorch", "tensorflow": "TensorFlow", "keras": "Keras",
        "mxnet": "MXNet", "jax": "JAX",
        "langchain": "LangChain", "llamaindex": "LlamaIndex",
        "autogpt": "AutoGPT", "babyagi": "BabyAGI",
        "crewai": "CrewAI", "autogen": "AutoGen",
        "react": "React", "vue": "Vue", "angular": "Angular",
        "flutter": "Flutter", "docker": "Docker",
        "kubernetes": "Kubernetes", "redis": "Redis",
        "mysql": "MySQL", "mongodb": "MongoDB",
        "postgresql": "PostgreSQL", "elasticsearch": "Elasticsearch",
        "clickhouse": "ClickHouse", "hbase": "HBase",
        "spark": "Spark", "flink": "Flink", "hadoop": "Hadoop",
        "hive": "Hive", "kafka": "Kafka", "airflow": "Airflow",
        "terraform": "Terraform", "ansible": "Ansible",
        "jenkins": "Jenkins", "prometheus": "Prometheus",
        "grafana": "Grafana", "github": "GitHub", "gitlab": "GitLab",
        "solidity": "Solidity", "istio": "Istio", "envoy": "Envoy",
        "helm": "Helm", "argocd": "ArgoCD", "tekton": "Tekton",
    }
