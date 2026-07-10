"""新一代信息技术技能分类体系（技能级粒度）"""

from typing import Optional

# 领域定义
DOMAINS = {
    "人工智能": {
        "description": "人工智能全栈技术",
        "subcategories": {
            "编程语言": ["Python", "R", "Julia", "C++"],
            "框架库": ["PyTorch", "TensorFlow", "Keras", "JAX", "MXNet", "PaddlePaddle"],
            "大语言模型": ["GPT系列", "Claude", "Llama", "Qwen", "文心一言", "通义千问", "DeepSeek",
                          "Prompt Engineering", "Chain-of-Thought", "RAG系统设计", "Fine-tuning",
                          "LoRA", "QLoRA", "RLHF", "DPO", "模型蒸馏"],
            "AI Agent": ["LangChain", "LlamaIndex", "LangGraph", "AutoGPT", "BabyAGI",
                        "CrewAI", "AutoGen", "工具调用", "Function Calling", "ReAct模式",
                        "多智能体协作", "Agent记忆系统", "Agent规划"],
            "NLP": ["分词", "命名实体识别", "情感分析", "文本分类", "机器翻译",
                   "信息抽取", "问答系统", "对话系统", "BERT", "RoBERTa", "LLaMA"],
            "计算机视觉": ["CNN", "RNN", "Transformer", "目标检测(YOLO/RCNN)", "图像分割",
                         "OCR", "人脸识别", "图像生成(Diffusion/GAN)", "视频分析", "多模态"],
            "传统ML": ["Scikit-learn", "XGBoost", "LightGBM", "CatBoost", "特征工程",
                     "模型评估", "A/B测试", "集成学习"]
        }
    },
    "大数据": {
        "description": "大数据处理与分析",
        "subcategories": {
            "计算引擎": ["Spark", "Flink", "Hadoop/MapReduce", "Storm", "Presto/Trino"],
            "存储系统": ["HDFS", "HBase", "Cassandra", "MongoDB", "Elasticsearch",
                       "ClickHouse", "Doris", "StarRocks"],
            "数仓体系": ["Hive", "数据湖(Iceberg/Hudi/Delta Lake)", "维度建模", "ETL/ELT"],
            "数据分析": ["SQL高级查询", "Pandas", "NumPy", "统计分析", "数据可视化(Tableau/PowerBI/Matplotlib)"]
        }
    },
    "云计算": {
        "description": "云原生与云计算平台",
        "subcategories": {
            "云平台": ["AWS", "阿里云", "腾讯云", "华为云", "Azure", "GCP", "Kubernetes"],
            "容器化": ["Docker", "containerd", "Podman", "镜像优化"],
            "服务网格": ["Istio", "Envoy", "Linkerd", "Consul"],
            "CI/CD": ["Jenkins", "GitLab CI", "GitHub Actions", "ArgoCD", "Tekton"],
            "IaC": ["Terraform", "Ansible", "CloudFormation", "Pulumi", "Helm"]
        }
    },
    "软件开发": {
        "description": "软件工程全栈技术",
        "subcategories": {
            "后端": ["Java/Spring Boot", "Go/Gin", "Python/FastAPI/Django/Flask",
                    "Node.js/Express/NestJS", "Ruby/Rails", "PHP/Laravel"],
            "前端": ["React/Vue/Angular", "TypeScript", "Next.js/Nuxt.js", "小程序开发",
                    "WebGL/Three.js", "TailwindCSS", "组件库设计"],
            "移动端": ["iOS(Swift/UIKit)", "Android(Kotlin/Jetpack)", "Flutter",
                      "React Native", "跨平台开发"],
            "架构设计": ["微服务架构", "分布式系统", "事件驱动架构", "DDD领域驱动设计",
                       "API设计(RESTful/GraphQL/gRPC)", "高并发", "高可用"]
        }
    },
    "DevOps": {
        "description": "开发运维一体化",
        "subcategories": {
            "监控告警": ["Prometheus", "Grafana", "ELK Stack", "Jaeger", "SkyWalking"],
            "可观测性": ["OpenTelemetry", "分布式追踪", "日志聚合"],
            "安全": ["DevSecOps", "容器安全", "WAF", "零信任架构", "渗透测试"]
        }
    },
    "区块链/Web3": {
        "description": "区块链与去中心化技术",
        "subcategories": {
            "公链": ["以太坊", "Solana", "Polygon", "Cosmos"],
            "智能合约": ["Solidity", "Rust(Substrate)", "Vyper", "合约审计"],
            "DeFi": ["DEX", "借贷协议", "稳定币", "流动性挖矿"],
            "基础设施": ["IPFS", "Web3.js/Ethers.js", "钱包集成", "跨链桥"]
        }
    },
    "网络安全": {
        "description": "信息安全技术",
        "subcategories": {
            "攻防": ["渗透测试", "漏洞挖掘", "逆向工程", "CTF竞赛"],
            "防护": ["防火墙", "IDS/IPS", "SIEM", "SOC"],
            "密码学": ["对称加密", "非对称加密", "数字签名", "零知识证明"]
        }
    },
    "物联网": {
        "description": "IoT全栈技术",
        "subcategories": {
            "嵌入式": ["RTOS", "嵌入式Linux", "MCU开发", "PCB设计"],
            "通信协议": ["MQTT", "CoAP", "Zigbee", "NB-IoT", "LoRa", "5G模组"],
            "平台": ["AWS IoT", "阿里IoT", "ThingsBoard", "边缘计算"]
        }
    }
}


# ===== 技能先修关系映射表 =====
PREREQUISITE_MAP = {
    "Python": [],
    "Java": [],
    "Go": [],
    "C++": [],
    "JavaScript": [],
    "TypeScript": ["JavaScript"],
    "SQL": [],
    "Pandas": ["Python"],
    "NumPy": ["Python"],
    "Scikit-learn": ["Python", "NumPy"],
    "PyTorch": ["Python", "NumPy"],
    "TensorFlow": ["Python", "NumPy"],
    "Keras": ["Python", "TensorFlow"],
    "FastAPI": ["Python"],
    "Django": ["Python"],
    "Flask": ["Python"],
    "Prompt Engineering": ["Python"],
    "LangChain": ["Python", "Prompt Engineering"],
    "LlamaIndex": ["Python", "Prompt Engineering"],
    "LangGraph": ["LangChain"],
    "RAG": ["LangChain", "向量数据库", "Embedding"],
    "RAG系统设计": ["LangChain", "向量数据库", "Embedding"],
    "Fine-tuning": ["PyTorch", "深度学习"],
    "LoRA": ["PyTorch", "Fine-tuning"],
    "QLoRA": ["LoRA"],
    "RLHF": ["Fine-tuning"],
    "DPO": ["Fine-tuning"],
    "Function Calling": ["LangChain", "Prompt Engineering"],
    "ReAct模式": ["LangChain", "Function Calling"],
    "AutoGPT": ["LangChain", "ReAct模式"],
    "多智能体协作": ["AutoGPT", "CrewAI"],
    "模型蒸馏": ["Fine-tuning", "大语言模型"],
    "Chain-of-Thought": ["Prompt Engineering"],
    "深度学习": ["Python", "机器学习", "线性代数"],
    "机器学习": ["Python", "统计学", "线性代数"],
    "Transformer": ["深度学习", "PyTorch"],
    "BERT": ["Transformer"],
    "目标检测(YOLO/RCNN)": ["CNN", "PyTorch"],
    "图像分割": ["CNN", "PyTorch"],
    "图像生成(Diffusion/GAN)": ["深度学习", "PyTorch"],
    "多模态": ["Transformer", "计算机视觉", "NLP"],
    "Hadoop": ["Java", "Linux"],
    "HDFS": ["Hadoop"],
    "Spark": ["Scala/Python", "Hadoop基础"],
    "Flink": ["Java/Scala", "流式计算概念"],
    "Hive": ["SQL", "Hadoop"],
    "Kafka": ["Java", "分布式系统概念"],
    "Airflow": ["Python", "ETL概念"],
    "数据湖(Iceberg/Hudi/Delta Lake)": ["Spark", "Hive"],
    "ETL/ELT": ["SQL", "数据仓库概念"],
    "MySQL": ["SQL"],
    "PostgreSQL": ["SQL"],
    "MongoDB": ["数据库基础概念"],
    "Redis": ["数据库基础概念"],
    "Elasticsearch": ["数据库基础概念"],
    "ClickHouse": ["SQL", "列式存储概念"],
    "HTML": [],
    "CSS": ["HTML"],
    "JavaScript": ["HTML", "CSS"],
    "React": ["JavaScript", "HTML", "CSS"],
    "Vue": ["JavaScript", "HTML", "CSS"],
    "Angular": ["JavaScript", "TypeScript"],
    "Next.js": ["React"],
    "Nuxt.js": ["Vue"],
    "Node.js": ["JavaScript"],
    "TailwindCSS": ["CSS"],
    "Java/Spring Boot": ["Java", "MySQL"],
    "Go/Gin": ["Go", "数据库基础概念"],
    "Python/FastAPI/Django/Flask": ["Python", "数据库基础概念"],
    "Node.js/Express/NestJS": ["Node.js"],
    "API设计(RESTful/GraphQL/gRPC)": ["编程语言基础", "HTTP协议"],
    "微服务架构": ["API设计", "分布式系统概念", "容器化"],
    "分布式系统": ["操作系统", "网络基础"],
    "Docker": ["Linux"],
    "Docker Compose": ["Docker"],
    "Kubernetes": ["Docker", "Linux"],
    "Helm": ["Kubernetes"],
    "Istio": ["Kubernetes"],
    "Terraform": ["云基础概念", "Docker"],
    "Ansible": ["Linux", "网络基础"],
    "Prometheus": ["Docker", "Linux"],
    "Grafana": ["Prometheus"],
    "Flutter": ["Dart", "移动开发基础"],
    "React Native": ["React", "JavaScript"],
    "iOS(Swift/UIKit)": ["Swift"],
    "Android(Kotlin/Jetpack)": ["Kotlin"],
    "渗透测试": ["网络基础", "操作系统", "Web基础"],
    "漏洞挖掘": ["渗透测试", "逆向工程"],
    "逆向工程": ["C/C++", "汇编基础"],
    "零信任架构": ["网络安全基础"],
    "嵌入式Linux": ["Linux", "C语言"],
    "RTOS": ["C语言", "嵌入式基础"],
    "边缘计算": ["嵌入式Linux", "云计算基础"],
    "Solidity": ["JavaScript", "以太坊基础"],
    "Web3.js/Ethers.js": ["JavaScript", "以太坊基础"],
    "Git": [],
    "Linux": [],
    "统计学": ["数学基础"],
    "线性代数": [],
}


def get_all_prerequisites() -> dict:
    """获取所有先修关系"""
    return dict(PREREQUISITE_MAP)


def get_prerequisites(skill: str) -> list[str]:
    """获取指定技能的先修技能"""
    return PREREQUISITE_MAP.get(skill, [])


def get_all_skills() -> list[str]:
    """获取所有技能的扁平列表"""
    skills = []
    for domain_data in DOMAINS.values():
        for cat_skills in domain_data["subcategories"].values():
            skills.extend(cat_skills)
    return skills


def get_domain_skills(domain: str) -> list[str]:
    """获取指定领域的所有技能"""
    if domain not in DOMAINS:
        return []
    skills = []
    for cat_skills in DOMAINS[domain]["subcategories"].values():
        skills.extend(cat_skills)
    return skills


def find_skill_domain(skill: str) -> Optional[str]:
    """查找技能所属领域"""
    for domain, data in DOMAINS.items():
        for cat_skills in data["subcategories"].values():
            if skill.lower() in [s.lower() for s in cat_skills]:
                return domain
    return None
