"""评测数据集 - 包含所有测试用例的标准化数据

每个测试用例包含:
    input: 输入数据 (JD原文/简历原文/人岗对)
    expected_output: 期望的结构化输出
    fields: 需要比较的字段定义
"""

# ============================================================
# JD解析测试用例（10条）
# ============================================================

JD_TEST_CASES = [
    {
        "id": "JD-001",
        "title": "Python后端开发工程师",
        "input": """【职位名称】Python后端开发工程师
【公司名称】字节跳动
【薪资范围】30K-60K/月
【工作地点】北京海淀区
【岗位职责】
1. 负责公司核心业务的后端服务设计与开发
2. 参与微服务架构的规划与落地
3. 优化系统性能，保障高并发场景下的稳定性
4. 编写单元测试和技术文档
【任职要求】
1. 本科及以上学历，计算机相关专业
2. 3-5年Python开发经验
3. 熟悉Django/Flask/FastAPI等Web框架
4. 掌握MySQL、Redis、消息队列等中间件
5. 了解Docker、Kubernetes容器化技术
6. 有微服务架构实战经验优先
【加分项】
- 有高并发系统设计经验
- 熟悉Go语言
- 开源项目贡献者""",
        "expected_output": {
            "job_title": "Python后端开发工程师",
            "company_name": "字节跳动",
            "salary_min": 30,
            "salary_max": 60,
            "location": "北京",
            "experience_min": 3,
            "experience_max": 5,
            "education": "本科",
            "required_skills": ["Python", "Django", "Flask", "FastAPI", "MySQL", "Redis", "消息队列", "Docker", "Kubernetes", "微服务"],
            "optional_skills": ["Go", "高并发"],
            "industry": "互联网",
            "job_description": "负责公司核心业务的后端服务设计与开发，参与微服务架构的规划与落地，优化系统性能，保障高并发场景下的稳定性，编写单元测试和技术文档"
        },
        "fields": ["job_title", "company_name", "salary_min", "salary_max", "location",
                    "experience_min", "experience_max", "education", "required_skills",
                    "optional_skills", "industry"]
    },
    {
        "id": "JD-002",
        "title": "前端架构师",
        "input": """【职位名称】前端架构师
【公司名称】阿里巴巴集团
【薪资范围】40K-70K/月
【工作地点】杭州余杭区
【岗位职责】
1. 负责前端技术架构规划与设计
2. 主导前端基础设施建设，提升开发效率
3. 负责核心模块的代码质量和性能优化
4. 指导初中级前端工程师成长
【任职要求】
1. 统招本科以上学历，5年以上前端开发经验
2. 精通JavaScript/TypeScript，熟悉ES6+规范
3. 深入理解React/Vue/Angular至少一种框架原理
4. 有前端工程化、Webpack/Vite构建工具经验
5. 熟悉Node.js服务端开发
6. 有大型项目架构经验
【加分项】
- 有移动端React Native或Flutter经验
- 了解WebAssembly
- 有技术博客或社区影响力""",
        "expected_output": {
            "job_title": "前端架构师",
            "company_name": "阿里巴巴集团",
            "salary_min": 40,
            "salary_max": 70,
            "location": "杭州",
            "experience_min": 5,
            "experience_max": 5,
            "education": "本科",
            "required_skills": ["JavaScript", "TypeScript", "React", "Vue", "Angular", "Webpack", "Vite", "Node.js", "前端工程化"],
            "optional_skills": ["React Native", "Flutter", "WebAssembly"],
            "industry": "互联网",
            "job_description": "负责前端技术架构规划与设计，主导前端基础设施建设，提升开发效率，负责核心模块的代码质量和性能优化，指导初中级前端工程师成长"
        },
        "fields": ["job_title", "company_name", "salary_min", "salary_max", "location",
                    "experience_min", "experience_max", "education", "required_skills",
                    "optional_skills", "industry"]
    },
    {
        "id": "JD-003",
        "title": "算法工程师（推荐系统）",
        "input": """【职位名称】算法工程师（推荐系统方向）
【公司名称】快手科技
【薪资范围】35K-65K/月
【工作地点】北京西二旗
【岗位职责】
1. 负责推荐系统的召回、排序算法的设计与优化
2. 基于用户行为数据构建用户兴趣模型
3. 探索深度学习在推荐场景的前沿应用
4. 通过A/B测试验证算法效果并持续迭代
【任职要求】
1. 硕士及以上学历，计算机/数学/统计相关专业
2. 3年以上推荐系统或机器学习相关经验
3. 精通Python/C++，熟悉TensorFlow或PyTorch
4. 深入理解协同过滤、FM/FFM、Wide&Deep等推荐算法
5. 有大规模数据处理经验（Hadoop/Spark）
6. 在KDD/RecSys/AAAI等会议发表过论文优先
【加分项】
- 熟悉图神经网络(GNN)
- 有多模态推荐经验
- Kaggle竞赛Top10%""",
        "expected_output": {
            "job_title": "算法工程师（推荐系统方向）",
            "company_name": "快手科技",
            "salary_min": 35,
            "salary_max": 65,
            "location": "北京",
            "experience_min": 3,
            "experience_max": 3,
            "education": "硕士",
            "required_skills": ["Python", "C++", "TensorFlow", "PyTorch", "协同过滤", "FM", "Wide&Deep", "Hadoop", "Spark", "推荐系统", "机器学习", "深度学习"],
            "optional_skills": ["图神经网络", "GNN", "多模态推荐", "Kaggle"],
            "industry": "互联网",
            "job_description": "负责推荐系统的召回、排序算法的设计与优化，基于用户行为数据构建用户兴趣模型，探索深度学习在推荐场景的前沿应用，通过A/B测试验证算法效果并持续迭代"
        },
        "fields": ["job_title", "company_name", "salary_min", "salary_max", "location",
                    "experience_min", "experience_max", "education", "required_skills",
                    "optional_skills", "industry"]
    },
    {
        "id": "JD-004",
        "title": "DevOps工程师",
        "input": """【职位名称】DevOps/SRE工程师
【公司名称】腾讯科技
【薪资范围】25K-50K/月
【工作地点】深圳南山区
【岗位职责】
1. 设计并维护CI/CD流水线，保障业务快速迭代
2. 负责Kubernetes集群的运维与优化
3. 建设监控告警体系（Prometheus/Grafana）
4. 参与容灾架构设计，提升系统SLA
5. 推动基础设施即代码（IaC）实践
【任职要求】
1. 本科及以上学历，3年以上运维开发经验
2. 精通Linux系统管理，熟悉Shell/Python/Go至少一种
3. 深入理解Docker、Kubernetes生态
4. 熟悉Jenkins/GitLab CI等CI/CD工具
5. 掌握Prometheus、Grafana、ELK等监控方案
6. 熟悉Terraform/Ansible等IaC工具
【加分项】
- 有混合云/多云管理经验
- CKA/CKS认证优先
- 有大规模集群管理经验""",
        "expected_output": {
            "job_title": "DevOps/SRE工程师",
            "company_name": "腾讯科技",
            "salary_min": 25,
            "salary_max": 50,
            "location": "深圳",
            "experience_min": 3,
            "experience_max": 3,
            "education": "本科",
            "required_skills": ["Linux", "Python", "Shell", "Docker", "Kubernetes", "Jenkins", "GitLab CI", "Prometheus", "Grafana", "ELK", "Terraform", "Ansible", "CI/CD"],
            "optional_skills": ["混合云", "多云"],
            "industry": "互联网",
            "job_description": "设计并维护CI/CD流水线，保障业务快速迭代，负责Kubernetes集群的运维与优化，建设监控告警体系（Prometheus/Grafana），参与容灾架构设计，提升系统SLA，推动基础设施即代码（IaC）实践"
        },
        "fields": ["job_title", "company_name", "salary_min", "salary_max", "location",
                    "experience_min", "experience_max", "education", "required_skills",
                    "optional_skills", "industry"]
    },
    {
        "id": "JD-005",
        "title": "产品经理（B端）",
        "input": """【职位名称】高级产品经理（企业服务方向）
【公司名称】用友网络
【薪资范围】20K-40K/月
【工作地点】北京海淀区
【岗位职责】
1. 负责企业级SaaS产品的需求分析和产品规划
2. 深入客户业务场景，输出高质量PRD
3. 协同设计、研发、测试团队推进产品交付
4. 跟踪产品数据，根据反馈持续优化产品体验
【任职要求】
1. 本科及以上学历，5年以上B端产品经验
2. 有ERP/CRM/OA等企业软件产品经验
3. 优秀的业务理解和逻辑分析能力
4. 熟练使用Axure/Sketch/Figma等原型工具
5. 有数据分析能力，熟练使用SQL
6. 具备良好的跨部门沟通能力
【加分项】
- 有SaaS产品从0到1经验
- 了解低代码/零代码平台
- PMP认证""",
        "expected_output": {
            "job_title": "高级产品经理（企业服务方向）",
            "company_name": "用友网络",
            "salary_min": 20,
            "salary_max": 40,
            "location": "北京",
            "experience_min": 5,
            "experience_max": 5,
            "education": "本科",
            "required_skills": ["Axure", "Sketch", "Figma", "SQL", "PRD", "B端产品", "数据分析"],
            "optional_skills": ["低代码", "零代码", "SaaS"],
            "industry": "企业服务",
            "job_description": "负责企业级SaaS产品的需求分析和产品规划，深入客户业务场景，输出高质量PRD，协同设计、研发、测试团队推进产品交付，跟踪产品数据，根据反馈持续优化产品体验"
        },
        "fields": ["job_title", "company_name", "salary_min", "salary_max", "location",
                    "experience_min", "experience_max", "education", "required_skills",
                    "optional_skills", "industry"]
    },
    {
        "id": "JD-006",
        "title": "数据分析师",
        "input": """【职位名称】数据分析师
【公司名称】美团
【薪资范围】18K-35K/月
【工作地点】上海杨浦区
【岗位职责】
1. 负责业务数据的提取、清洗和分析，输出数据报告
2. 搭建业务监控指标体系，建设数据看板
3. 通过AB实验分析驱动业务决策
4. 与运营、产品团队协作，发现增长机会
【任职要求】
1. 本科及以上学历，统计学/数学/计算机相关专业
2. 2年以上数据分析经验
3. 精通SQL，熟悉Python或R数据分析
4. 熟练使用Tableau/FineBI/QuickBI等BI工具
5. 扎实的统计学基础，了解假设检验、回归分析
6. 优秀的业务理解和沟通表达能力
【加分项】
- 有互联网大厂经验
- 熟悉数据仓库和数据建模
- 有用户增长分析经验""",
        "expected_output": {
            "job_title": "数据分析师",
            "company_name": "美团",
            "salary_min": 18,
            "salary_max": 35,
            "location": "上海",
            "experience_min": 2,
            "experience_max": 2,
            "education": "本科",
            "required_skills": ["SQL", "Python", "R", "Tableau", "FineBI", "QuickBI", "数据分析", "统计学", "假设检验", "回归分析"],
            "optional_skills": ["数据仓库", "数据建模", "用户增长"],
            "industry": "互联网",
            "job_description": "负责业务数据的提取、清洗和分析，输出数据报告，搭建业务监控指标体系，建设数据看板，通过AB实验分析驱动业务决策，与运营、产品团队协作，发现增长机会"
        },
        "fields": ["job_title", "company_name", "salary_min", "salary_max", "location",
                    "experience_min", "experience_max", "education", "required_skills",
                    "optional_skills", "industry"]
    },
    {
        "id": "JD-007",
        "title": "Java开发工程师",
        "input": """【职位名称】Java开发工程师
【公司名称】京东集团
【薪资范围】25K-50K/月
【工作地点】北京亦庄
【岗位职责】
1. 负责京东零售核心系统的设计与开发
2. 参与高并发、高可用分布式系统建设
3. 负责代码Review和技术方案评审
4. 解决线上疑难问题，持续优化系统性能
【任职要求】
1. 本科及以上学历，计算机相关专业
2. 4-8年Java开发经验
3. 精通Java，熟悉Spring Boot/Spring Cloud微服务栈
4. 熟悉MySQL、Redis、Elasticsearch、MQ等中间件
5. 了解分布式事务、限流、降级等架构设计
6. 有电商系统开发经验优先
【加分项】
- 熟悉Go或Kotlin
- 有高并发调优经验
- 有技术专利或知名开源项目""",
        "expected_output": {
            "job_title": "Java开发工程师",
            "company_name": "京东集团",
            "salary_min": 25,
            "salary_max": 50,
            "location": "北京",
            "experience_min": 4,
            "experience_max": 8,
            "education": "本科",
            "required_skills": ["Java", "Spring Boot", "Spring Cloud", "MySQL", "Redis", "Elasticsearch", "MQ", "消息队列", "分布式"],
            "optional_skills": ["Go", "Kotlin", "高并发"],
            "industry": "电商",
            "job_description": "负责京东零售核心系统的设计与开发，参与高并发、高可用分布式系统建设，负责代码Review和技术方案评审，解决线上疑难问题，持续优化系统性能"
        },
        "fields": ["job_title", "company_name", "salary_min", "salary_max", "location",
                    "experience_min", "experience_max", "education", "required_skills",
                    "optional_skills", "industry"]
    },
    {
        "id": "JD-008",
        "title": "测试开发工程师",
        "input": """【职位名称】测试开发工程师
【公司名称】百度
【薪资范围】20K-40K/月
【工作地点】北京百度大厦
【岗位职责】
1. 负责产品质量保障，设计并执行测试策略
2. 开发自动化测试框架和测试工具
3. 搭建CI/CD流水线中的质量门禁
4. 引入性能测试和安全测试能力
【任职要求】
1. 本科及以上学历，3年以上测试开发经验
2. 精通Python或Java，能独立开发测试框架
3. 熟悉Selenium/Appium/Cypress等自动化工具
4. 掌握性能测试工具（JMeter/Locust）
5. 有接口测试和契约测试经验
6. 了解持续集成和持续交付理念
【加分项】
- 有安全测试经验
- 有测试平台开发经验
- 有AI产品测试经验""",
        "expected_output": {
            "job_title": "测试开发工程师",
            "company_name": "百度",
            "salary_min": 20,
            "salary_max": 40,
            "location": "北京",
            "experience_min": 3,
            "experience_max": 3,
            "education": "本科",
            "required_skills": ["Python", "Java", "Selenium", "Appium", "Cypress", "JMeter", "Locust", "自动化测试", "性能测试", "接口测试", "CI/CD"],
            "optional_skills": ["安全测试", "AI测试"],
            "industry": "互联网",
            "job_description": "负责产品质量保障，设计并执行测试策略，开发自动化测试框架和测试工具，搭建CI/CD流水线中的质量门禁，引入性能测试和安全测试能力"
        },
        "fields": ["job_title", "company_name", "salary_min", "salary_max", "location",
                    "experience_min", "experience_max", "education", "required_skills",
                    "optional_skills", "industry"]
    },
    {
        "id": "JD-009",
        "title": "安全工程师",
        "input": """【职位名称】安全工程师（应用安全方向）
【公司名称】华为技术有限公司
【薪资范围】30K-55K/月
【工作地点】东莞松山湖
【岗位职责】
1. 负责产品安全架构评审和代码审计
2. 建设SDL安全开发生命周期流程
3. 参与安全应急响应和漏洞挖掘
4. 推动安全工具链的集成与自动化
【任职要求】
1. 本科及以上学历，信息安全/计算机相关专业
2. 4年以上安全领域工作经验
3. 熟悉OWASP Top10漏洞原理及防护方案
4. 掌握Web安全、移动安全、云安全至少一个方向
5. 熟悉渗透测试方法和工具（Burp Suite/Nmap等）
6. 有CVE或安全论文发表经历优先
【加分项】
- 持有CISSP/CISP/OSCP等安全认证
- 有安全工具开发经验
- 熟悉零信任架构""",
        "expected_output": {
            "job_title": "安全工程师（应用安全方向）",
            "company_name": "华为技术有限公司",
            "salary_min": 30,
            "salary_max": 55,
            "location": "东莞",
            "experience_min": 4,
            "experience_max": 4,
            "education": "本科",
            "required_skills": ["OWASP Top10", "Web安全", "移动安全", "云安全", "渗透测试", "Burp Suite", "Nmap", "代码审计", "SDL"],
            "optional_skills": ["CISSP", "CISP", "OSCP", "零信任"],
            "industry": "通信/IT",
            "job_description": "负责产品安全架构评审和代码审计，建设SDL安全开发生命周期流程，参与安全应急响应和漏洞挖掘，推动安全工具链的集成与自动化"
        },
        "fields": ["job_title", "company_name", "salary_min", "salary_max", "location",
                    "experience_min", "experience_max", "education", "required_skills",
                    "optional_skills", "industry"]
    },
    {
        "id": "JD-010",
        "title": "AI产品经理",
        "input": """【职位名称】AI产品经理（AIGC方向）
【公司名称】字节跳动
【薪资范围】35K-60K/月
【工作地点】北京海淀区
【岗位职责】
1. 负责AIGC方向的产品规划和需求定义
2. 跟踪大模型（LLM）行业最新进展，探索产品应用场景
3. 设计AI产品的交互体验和效果评估体系
4. 协调算法、工程团队推动产品落地
【任职要求】
1. 本科及以上学历，计算机/AI相关背景优先
2. 3年以上互联网产品经验，其中1年以上AI产品经验
3. 对GPT、文心一言等大模型产品有深入体验和理解
4. 了解机器学习/深度学习基本概念
5. 数据驱动，熟练使用SQL和产品分析工具
6. 对AI技术趋势有敏锐的洞察力
【加分项】
- 有AI产品从0到1经验
- 有技术背景（能理解算法原理）
- 有海外AI产品经验""",
        "expected_output": {
            "job_title": "AI产品经理（AIGC方向）",
            "company_name": "字节跳动",
            "salary_min": 35,
            "salary_max": 60,
            "location": "北京",
            "experience_min": 3,
            "experience_max": 3,
            "education": "本科",
            "required_skills": ["SQL", "AIGC", "大模型", "LLM", "机器学习", "深度学习", "产品设计", "数据分析"],
            "optional_skills": ["AI产品", "算法"],
            "industry": "互联网",
            "job_description": "负责AIGC方向的产品规划和需求定义，跟踪大模型（LLM）行业最新进展，探索产品应用场景，设计AI产品的交互体验和效果评估体系，协调算法、工程团队推动产品落地"
        },
        "fields": ["job_title", "company_name", "salary_min", "salary_max", "location",
                    "experience_min", "experience_max", "education", "required_skills",
                    "optional_skills", "industry"]
    },
]

# ============================================================
# 简历解析测试用例（5份）
# ============================================================

RESUME_TEST_CASES = [
    {
        "id": "RES-001",
        "title": "资深Python后端工程师简历",
        "input": """姓名：张明
电话：13800138001
邮箱：zhangming@example.com
性别：男
年龄：32

教育背景
2012.09 - 2016.06  北京大学  计算机科学与技术  本科
2016.09 - 2019.06  清华大学  软件工程  硕士

工作经历
2019.07 - 2022.03  阿里巴巴  后端开发工程师
- 负责电商订单系统的微服务化改造，将单体架构拆分为12个微服务
- 设计并实现了分布式事务解决方案，保障了订单支付的一致性
- 使用Python/Java开发高并发接口，QPS提升至5万+

2022.04 - 至今  字节跳动  高级后端开发工程师
- 主导抖音电商后台架构升级，支撑日活2亿用户
- 设计实时数据管道，使用Kafka+Flink处理千万级事件
- 推动服务网格（Istio）落地，降低服务间调用延迟30%
- 负责技术团队Code Review，指导3名初中级工程师

项目经验
项目一：分布式链路追踪系统
- 基于OpenTelemetry构建全链路追踪平台
- 支持每秒10万+ Span的采集和处理
- 技术栈：Python, Go, Elasticsearch, Jaeger, Kafka

项目二：AI驱动的智能运维平台
- 使用机器学习预测系统异常，提前发现90%的故障
- 集成Prometheus+Grafana监控体系
- 技术栈：Python, TensorFlow, Prometheus, Kubernetes

技能
Python, Java, Go, Django, FastAPI, Flask, MySQL, Redis, Kafka, Flink, Docker, Kubernetes, Istio, Prometheus, Grafana, Elasticsearch, OpenTelemetry, TensorFlow, 微服务架构, 系统设计, 分布式系统

证书
- AWS Certified Solutions Architect
- CKA（Certified Kubernetes Administrator）""",
        "expected_output": {
            "name": "张明",
            "phone": "13800138001",
            "email": "zhangming@example.com",
            "gender": "男",
            "age": 32,
            "education": [
                {"school": "北京大学", "degree": "本科", "major": "计算机科学与技术", "graduation_date": "2016.06"},
                {"school": "清华大学", "degree": "硕士", "major": "软件工程", "graduation_date": "2019.06"}
            ],
            "work_experience": [
                {"company": "阿里巴巴", "position": "后端开发工程师", "start_date": "2019.07", "end_date": "2022.03"},
                {"company": "字节跳动", "position": "高级后端开发工程师", "start_date": "2022.04", "end_date": "至今"}
            ],
            "total_experience_years": 7,
            "skills_explicit": ["Python", "Java", "Go", "Django", "FastAPI", "Flask", "MySQL", "Redis", "Kafka", "Flink", "Docker", "Kubernetes", "Istio", "Prometheus", "Grafana", "Elasticsearch", "OpenTelemetry", "TensorFlow", "微服务架构", "系统设计", "分布式系统"],
            "skills_implicit": [],
            "overall_technical_level": "senior"
        },
        "fields": ["name", "phone", "email", "gender", "age", "education", "work_experience",
                    "total_experience_years", "skills_explicit", "overall_technical_level"]
    },
    {
        "id": "RES-002",
        "title": "全栈开发工程师简历",
        "input": """姓名：李婷
电话：13900139002
邮箱：liting@example.com
性别：女
年龄：28

教育背景
2013.09 - 2017.06  浙江大学  计算机科学与技术  本科

工作经历
2017.08 - 2020.05  网易  前端开发工程师
- 负责网易云音乐Web版的前端开发
- 使用React+Redux构建复杂的音乐播放交互
- 优化首屏加载性能，LCP从3s降低至1.2s
- 封装了通用的UI组件库，提升团队开发效率

2020.06 - 至今  小红书  全栈开发工程师
- 负责社区Feed流系统的前后端全栈开发
- 使用Vue3+TypeScript重构了移动端H5页面
- 基于Node.js+Express开发BFF层聚合接口
- 使用Python编写数据清洗脚本，支持运营数据分析
- 参与技术方案评审，推动前端工程化建设

项目经验
项目一：实时协作白板
- 基于WebSocket实现多人实时协作编辑
- 支持Canvas绘图和图形变换
- 技术栈：React, TypeScript, Socket.io, Canvas, Node.js

项目二：微前端治理平台
- 使用qiankun框架实现微前端架构
- 统一了多个子应用的鉴权和路由管理
- 技术栈：Vue3, qiankun, Webpack, Module Federation

技能
JavaScript, TypeScript, React, Vue3, Redux, Node.js, Express, Python, HTML5, CSS3, Webpack, Vite, Socket.io, Canvas, WebSocket, Git, Docker, MySQL, MongoDB

证书
- 无""",
        "expected_output": {
            "name": "李婷",
            "phone": "13900139002",
            "email": "liting@example.com",
            "gender": "女",
            "age": 28,
            "education": [
                {"school": "浙江大学", "degree": "本科", "major": "计算机科学与技术", "graduation_date": "2017.06"}
            ],
            "work_experience": [
                {"company": "网易", "position": "前端开发工程师", "start_date": "2017.08", "end_date": "2020.05"},
                {"company": "小红书", "position": "全栈开发工程师", "start_date": "2020.06", "end_date": "至今"}
            ],
            "total_experience_years": 9,
            "skills_explicit": ["JavaScript", "TypeScript", "React", "Vue3", "Redux", "Node.js", "Express", "Python", "HTML5", "CSS3", "Webpack", "Vite", "Socket.io", "Canvas", "WebSocket", "Git", "Docker", "MySQL", "MongoDB"],
            "skills_implicit": [],
            "overall_technical_level": "mid"
        },
        "fields": ["name", "phone", "email", "gender", "age", "education", "work_experience",
                    "total_experience_years", "skills_explicit", "overall_technical_level"]
    },
    {
        "id": "RES-003",
        "title": "数据分析师简历",
        "input": """姓名：王芳
电话：13700137003
邮箱：wangfang@example.com
性别：女
年龄：27

教育背景
2014.09 - 2018.06  复旦大学  统计学  本科
2018.09 - 2020.06  上海交通大学  应用统计  硕士

工作经历
2020.07 - 2022.08  拼多多  数据分析师
- 负责拼多多用户增长方向的数据分析
- 搭建用户留存分析模型，识别核心留存因子
- 设计AB实验框架，推动实验规范化
- 输出月度数据洞察报告，直接支持运营决策

2022.09 - 至今  蚂蚁集团  高级数据分析师
- 负责支付宝支付业务的数据体系建设
- 构建用户支付行为预测模型（XGBoost），AUC达0.85
- 设计业务指标异动归因框架，定位问题效率提升50%
- 使用Python开发自动化报表系统，节省团队30%工时

项目经验
项目一：用户流失预警系统
- 基于用户历史行为数据构建流失概率预测模型
- 使用逻辑回归+随机森林集成方法，准确率87%
- 技术栈：Python, Scikit-learn, Pandas, SQL, Tableau

项目二：数据质量监控平台
- 设计数据质量监控指标体系（完整性/准确性/一致性）
- 开发自动化数据校验工具，每日覆盖500+数据表
- 技术栈：Python, Airflow, MySQL, Grafana

技能
Python, R, SQL, Tableau, FineBI, Scikit-learn, XGBoost, Pandas, NumPy, Airflow, Excel, SPSS, AB实验, 假设检验, 回归分析, 聚类分析, 数据可视化

证书
- 数据分析师（CDA）二级认证""",
        "expected_output": {
            "name": "王芳",
            "phone": "13700137003",
            "email": "wangfang@example.com",
            "gender": "女",
            "age": 27,
            "education": [
                {"school": "复旦大学", "degree": "本科", "major": "统计学", "graduation_date": "2018.06"},
                {"school": "上海交通大学", "degree": "硕士", "major": "应用统计", "graduation_date": "2020.06"}
            ],
            "work_experience": [
                {"company": "拼多多", "position": "数据分析师", "start_date": "2020.07", "end_date": "2022.08"},
                {"company": "蚂蚁集团", "position": "高级数据分析师", "start_date": "2022.09", "end_date": "至今"}
            ],
            "total_experience_years": 6,
            "skills_explicit": ["Python", "R", "SQL", "Tableau", "FineBI", "Scikit-learn", "XGBoost", "Pandas", "NumPy", "Airflow", "Excel", "SPSS", "AB实验", "假设检验", "回归分析", "聚类分析", "数据可视化"],
            "skills_implicit": [],
            "overall_technical_level": "mid"
        },
        "fields": ["name", "phone", "email", "gender", "age", "education", "work_experience",
                    "total_experience_years", "skills_explicit", "overall_technical_level"]
    },
    {
        "id": "RES-004",
        "title": "Java架构师简历",
        "input": """姓名：赵强
电话：13600136004
邮箱：zhaoqiang@example.com
性别：男
年龄：38

教育背景
2005.09 - 2009.06  华中科技大学  计算机科学与技术  本科
2009.09 - 2012.06  中国科学院大学  计算机系统结构  硕士

工作经历
2012.07 - 2015.08  百度   Java开发工程师
- 参与百度搜索广告系统的开发与维护
- 负责广告检索模块的性能优化
- 使用Java+Spring开发高并发广告投放服务

2015.09 - 2019.12  美团  高级Java开发工程师
- 负责美团外卖订单系统的架构升级
- 设计分布式任务调度平台，支撑日均1000万订单
- 主导MySQL分库分表方案设计，解决数据瓶颈
- 推动RPC框架从Dubbo迁移到gRPC

2020.01 - 至今  滴滴出行  技术专家/架构师
- 负责滴滴出行核心交易系统的架构设计
- 设计高可用架构方案，保障SLA 99.99%
- 制定团队技术规范和技术 roadmap
- 负责技术团队搭建和人才培养（管理15人团队）

项目经验
项目一：分布式消息中间件平台
- 基于RocketMQ二次开发，支持百万级TPS消息吞吐
- 设计消息轨迹和死信队列机制
- 技术栈：Java, RocketMQ, ZooKeeper, Netty

项目二：全链路压测平台
- 设计全链路压测方案，支持亿级流量模拟
- 开发流量录制和回放工具
- 技术栈：Java, Spring Cloud, Kubernetes, Prometheus

技能
Java, Spring Boot, Spring Cloud, Spring, Dubbo, gRPC, MySQL, Redis, RocketMQ, Kafka, ZooKeeper, Netty, Docker, Kubernetes, Prometheus, 微服务架构, 高并发, 分布式系统, 架构设计, 系统设计

证书
- 无""",
        "expected_output": {
            "name": "赵强",
            "phone": "13600136004",
            "email": "zhaoqiang@example.com",
            "gender": "男",
            "age": 38,
            "education": [
                {"school": "华中科技大学", "degree": "本科", "major": "计算机科学与技术", "graduation_date": "2009.06"},
                {"school": "中国科学院大学", "degree": "硕士", "major": "计算机系统结构", "graduation_date": "2012.06"}
            ],
            "work_experience": [
                {"company": "百度", "position": "Java开发工程师", "start_date": "2012.07", "end_date": "2015.08"},
                {"company": "美团", "position": "高级Java开发工程师", "start_date": "2015.09", "end_date": "2019.12"},
                {"company": "滴滴出行", "position": "技术专家/架构师", "start_date": "2020.01", "end_date": "至今"}
            ],
            "total_experience_years": 14,
            "skills_explicit": ["Java", "Spring Boot", "Spring Cloud", "Spring", "Dubbo", "gRPC", "MySQL", "Redis", "RocketMQ", "Kafka", "ZooKeeper", "Netty", "Docker", "Kubernetes", "Prometheus", "微服务架构", "高并发", "分布式系统", "架构设计", "系统设计"],
            "skills_implicit": [],
            "overall_technical_level": "expert"
        },
        "fields": ["name", "phone", "email", "gender", "age", "education", "work_experience",
                    "total_experience_years", "skills_explicit", "overall_technical_level"]
    },
    {
        "id": "RES-005",
        "title": "DevOps工程师简历",
        "input": """姓名：陈龙
电话：13500135005
邮箱：chenlong@example.com
性别：男
年龄：30

教育背景
2013.09 - 2017.06  武汉大学  软件工程  本科

工作经历
2017.07 - 2020.08  中兴通讯  运维工程师
- 负责公司内部DevOps平台的建设和维护
- 搭建Jenkins+GitLab CI流水线，实现自动化构建部署
- 管理200+台Linux服务器的日常运维
- 编写Python自动化脚本，提升运维效率40%

2020.09 - 至今  字节跳动  SRE/DevOps工程师
- 负责TikTok海外业务的基础设施运维
- 管理3000+节点的Kubernetes集群
- 建设Prometheus+Grafana+AlertManager监控体系
- 设计多活容灾架构，支撑全球化业务
- 开发故障自愈系统，平均MTTR降低60%

项目经验
项目一：混沌工程平台
- 设计并实现故障注入平台，验证系统容灾能力
- 支持CPU/内存/网络/磁盘等故障场景
- 技术栈：Go, Kubernetes, Chaos Mesh, Argo

项目二：云原生成本优化平台
- 分析Kubernetes集群资源利用率，优化资源分配
- 实现自动扩缩容策略，节省云成本30%
- 技术栈：Python, Kubernetes, Prometheus, Terraform, AWS

技能
Linux, Kubernetes, Docker, Jenkins, GitLab CI, Prometheus, Grafana, AlertManager, Terraform, Ansible, Python, Go, Shell, AWS, Argo, Chaos Mesh, Istio, Helm, ELK, CI/CD, SRE

证书
- CKA（Certified Kubernetes Administrator）
- AWS Certified DevOps Engineer""",
        "expected_output": {
            "name": "陈龙",
            "phone": "13500135005",
            "email": "chenlong@example.com",
            "gender": "男",
            "age": 30,
            "education": [
                {"school": "武汉大学", "degree": "本科", "major": "软件工程", "graduation_date": "2017.06"}
            ],
            "work_experience": [
                {"company": "中兴通讯", "position": "运维工程师", "start_date": "2017.07", "end_date": "2020.08"},
                {"company": "字节跳动", "position": "SRE/DevOps工程师", "start_date": "2020.09", "end_date": "至今"}
            ],
            "total_experience_years": 9,
            "skills_explicit": ["Linux", "Kubernetes", "Docker", "Jenkins", "GitLab CI", "Prometheus", "Grafana", "AlertManager", "Terraform", "Ansible", "Python", "Go", "Shell", "AWS", "Argo", "Chaos Mesh", "Istio", "Helm", "ELK", "CI/CD", "SRE"],
            "skills_implicit": [],
            "overall_technical_level": "senior"
        },
        "fields": ["name", "phone", "email", "gender", "age", "education", "work_experience",
                    "total_experience_years", "skills_explicit", "overall_technical_level"]
    },
]

# ============================================================
# 人岗匹配测试用例（20个）
# ============================================================

MATCH_TEST_CASES = [
    # 匹配对（label=1）
    {
        "id": "MATCH-001",
        "label": 1,
        "resume": {
            "skills": ["Python", "Django", "FastAPI", "MySQL", "Redis", "Docker", "Kubernetes", "消息队列", "微服务", "Go"],
            "implicit_skills": ["分布式系统", "高并发"],
            "skills_with_credibility": [
                {"skill_name": "Python", "credibility_score": 0.95},
                {"skill_name": "Django", "credibility_score": 0.90},
                {"skill_name": "FastAPI", "credibility_score": 0.85},
                {"skill_name": "MySQL", "credibility_score": 0.90},
                {"skill_name": "Docker", "credibility_score": 0.85},
                {"skill_name": "Kubernetes", "credibility_score": 0.80},
                {"skill_name": "微服务", "credibility_score": 0.85},
            ],
            "embedding": None
        },
        "job": {
            "title": "Python后端开发工程师",
            "required_skills": ["Python", "Django", "FastAPI", "MySQL", "Redis", "Docker", "Kubernetes", "微服务"],
            "optional_skills": ["Go", "高并发"],
            "embedding": None
        },
        "description": "Python后端工程师匹配Python后端开发岗位 - 技能高度匹配"
    },
    {
        "id": "MATCH-002",
        "label": 1,
        "resume": {
            "skills": ["React", "TypeScript", "JavaScript", "Vue", "Webpack", "Vite", "Node.js", "HTML5", "CSS3", "前端工程化"],
            "implicit_skills": ["前端架构", "性能优化"],
            "skills_with_credibility": [
                {"skill_name": "React", "credibility_score": 0.95},
                {"skill_name": "TypeScript", "credibility_score": 0.90},
                {"skill_name": "Vue", "credibility_score": 0.85},
                {"skill_name": "Node.js", "credibility_score": 0.80},
                {"skill_name": "Webpack", "credibility_score": 0.90},
            ],
            "embedding": None
        },
        "job": {
            "title": "前端架构师",
            "required_skills": ["JavaScript", "TypeScript", "React", "Vue", "Webpack", "Node.js", "前端工程化"],
            "optional_skills": ["WebAssembly"],
            "embedding": None
        },
        "description": "全栈工程师匹配前端架构师岗位 - 核心前端技能充分覆盖"
    },
    {
        "id": "MATCH-003",
        "label": 1,
        "resume": {
            "skills": ["Python", "TensorFlow", "PyTorch", "推荐系统", "机器学习", "深度学习", "Hadoop", "Spark", "协同过滤", "数据挖掘"],
            "implicit_skills": ["图神经网络", "FM"],
            "skills_with_credibility": [
                {"skill_name": "Python", "credibility_score": 0.90},
                {"skill_name": "TensorFlow", "credibility_score": 0.85},
                {"skill_name": "PyTorch", "credibility_score": 0.80},
                {"skill_name": "推荐系统", "credibility_score": 0.90},
                {"skill_name": "机器学习", "credibility_score": 0.85},
            ],
            "embedding": None
        },
        "job": {
            "title": "算法工程师（推荐系统方向）",
            "required_skills": ["Python", "TensorFlow", "PyTorch", "推荐系统", "机器学习", "深度学习", "Hadoop", "Spark", "协同过滤"],
            "optional_skills": ["图神经网络", "GNN", "多模态推荐"],
            "embedding": None
        },
        "description": "算法工程师匹配推荐系统岗位 - 推荐算法栈高度一致"
    },
    {
        "id": "MATCH-004",
        "label": 1,
        "resume": {
            "skills": ["Linux", "Docker", "Kubernetes", "Jenkins", "Prometheus", "Grafana", "Terraform", "Ansible", "Python", "Shell", "CI/CD", "ELK"],
            "implicit_skills": ["SRE", "容器化", "IaC"],
            "skills_with_credibility": [
                {"skill_name": "Linux", "credibility_score": 0.95},
                {"skill_name": "Kubernetes", "credibility_score": 0.90},
                {"skill_name": "Docker", "credibility_score": 0.95},
                {"skill_name": "Jenkins", "credibility_score": 0.90},
                {"skill_name": "Prometheus", "credibility_score": 0.85},
            ],
            "embedding": None
        },
        "job": {
            "title": "DevOps/SRE工程师",
            "required_skills": ["Linux", "Docker", "Kubernetes", "Jenkins", "GitLab CI", "Prometheus", "Grafana", "ELK", "Terraform", "Ansible", "Python", "Shell", "CI/CD"],
            "optional_skills": ["混合云", "多云"],
            "embedding": None
        },
        "description": "DevOps工程师匹配DevOps岗位 - 技能完全覆盖核心要求"
    },
    {
        "id": "MATCH-005",
        "label": 1,
        "resume": {
            "skills": ["Java", "Spring Boot", "Spring Cloud", "MySQL", "Redis", "消息队列", "分布式", "高并发", "微服务", "Dubbo"],
            "implicit_skills": ["系统设计", "架构设计"],
            "skills_with_credibility": [
                {"skill_name": "Java", "credibility_score": 0.95},
                {"skill_name": "Spring Boot", "credibility_score": 0.90},
                {"skill_name": "Spring Cloud", "credibility_score": 0.85},
                {"skill_name": "MySQL", "credibility_score": 0.90},
                {"skill_name": "分布式", "credibility_score": 0.80},
            ],
            "embedding": None
        },
        "job": {
            "title": "Java开发工程师",
            "required_skills": ["Java", "Spring Boot", "Spring Cloud", "MySQL", "Redis", "Elasticsearch", "MQ", "分布式"],
            "optional_skills": ["Go", "Kotlin", "高并发"],
            "embedding": None
        },
        "description": "Java架构师匹配Java开发岗位 - 技能全面超越要求"
    },
    {
        "id": "MATCH-006",
        "label": 1,
        "resume": {
            "skills": ["Python", "SQL", "Tableau", "数据分析", "统计学", "假设检验", "回归分析", "Scikit-learn", "Pandas", "Excel", "数据可视化", "AB实验"],
            "implicit_skills": ["用户增长", "数据建模"],
            "skills_with_credibility": [
                {"skill_name": "SQL", "credibility_score": 0.95},
                {"skill_name": "Python", "credibility_score": 0.90},
                {"skill_name": "Tableau", "credibility_score": 0.85},
                {"skill_name": "数据分析", "credibility_score": 0.90},
                {"skill_name": "统计学", "credibility_score": 0.85},
            ],
            "embedding": None
        },
        "job": {
            "title": "数据分析师",
            "required_skills": ["SQL", "Python", "Tableau", "数据分析", "统计学", "假设检验", "回归分析"],
            "optional_skills": ["数据仓库", "数据建模", "用户增长"],
            "embedding": None
        },
        "description": "数据分析师匹配数据分析岗位 - 核心技能完全匹配"
    },
    {
        "id": "MATCH-007",
        "label": 1,
        "resume": {
            "skills": ["Python", "Java", "Selenium", "Appium", "JMeter", "自动化测试", "性能测试", "接口测试", "CI/CD", "Linux"],
            "implicit_skills": ["质量保障", "测试框架设计"],
            "skills_with_credibility": [
                {"skill_name": "Python", "credibility_score": 0.90},
                {"skill_name": "Java", "credibility_score": 0.80},
                {"skill_name": "Selenium", "credibility_score": 0.90},
                {"skill_name": "Appium", "credibility_score": 0.80},
                {"skill_name": "JMeter", "credibility_score": 0.85},
            ],
            "embedding": None
        },
        "job": {
            "title": "测试开发工程师",
            "required_skills": ["Python", "Java", "Selenium", "Appium", "JMeter", "自动化测试", "性能测试", "接口测试", "CI/CD"],
            "optional_skills": ["安全测试", "AI测试"],
            "embedding": None
        },
        "description": "测试开发工程师匹配测试开发岗位 - 必备技能齐全"
    },
    {
        "id": "MATCH-008",
        "label": 1,
        "resume": {
            "skills": ["Linux", "Python", "Go", "Web安全", "渗透测试", "Burp Suite", "Nmap", "代码审计", "SDL", "Docker", "Kubernetes"],
            "implicit_skills": ["安全架构", "零信任"],
            "skills_with_credibility": [
                {"skill_name": "Web安全", "credibility_score": 0.90},
                {"skill_name": "渗透测试", "credibility_score": 0.85},
                {"skill_name": "Burp Suite", "credibility_score": 0.90},
                {"skill_name": "Nmap", "credibility_score": 0.85},
                {"skill_name": "代码审计", "credibility_score": 0.80},
            ],
            "embedding": None
        },
        "job": {
            "title": "安全工程师（应用安全方向）",
            "required_skills": ["Web安全", "渗透测试", "Burp Suite", "Nmap", "代码审计", "SDL", "OWASP Top10", "移动安全"],
            "optional_skills": ["CISSP", "零信任"],
            "embedding": None
        },
        "description": "安全工程师匹配安全岗位 - 应用安全技能匹配度高"
    },
    {
        "id": "MATCH-009",
        "label": 1,
        "resume": {
            "skills": ["SQL", "AIGC", "大模型", "产品设计", "数据分析", "机器学习", "深度学习", "Python", "用户研究", "PRD"],
            "implicit_skills": ["AI产品", "LLM"],
            "skills_with_credibility": [
                {"skill_name": "AIGC", "credibility_score": 0.85},
                {"skill_name": "大模型", "credibility_score": 0.80},
                {"skill_name": "产品设计", "credibility_score": 0.90},
                {"skill_name": "数据分析", "credibility_score": 0.85},
                {"skill_name": "机器学习", "credibility_score": 0.70},
            ],
            "embedding": None
        },
        "job": {
            "title": "AI产品经理（AIGC方向）",
            "required_skills": ["SQL", "AIGC", "大模型", "LLM", "产品设计", "数据分析", "机器学习"],
            "optional_skills": ["AI产品", "算法"],
            "embedding": None
        },
        "description": "AI产品经理匹配AI产品经理岗位 - AIGC和大模型经验匹配"
    },
    {
        "id": "MATCH-010",
        "label": 1,
        "resume": {
            "skills": ["Python", "数据分析", "SQL", "Tableau", "Excel", "统计学", "回归分析", "AB实验", "数据可视化", "Pandas"],
            "implicit_skills": ["业务分析", "数据驱动"],
            "skills_with_credibility": [
                {"skill_name": "Python", "credibility_score": 0.85},
                {"skill_name": "SQL", "credibility_score": 0.90},
                {"skill_name": "数据分析", "credibility_score": 0.90},
                {"skill_name": "统计学", "credibility_score": 0.80},
                {"skill_name": "AB实验", "credibility_score": 0.75},
            ],
            "embedding": None
        },
        "job": {
            "title": "数据分析师",
            "required_skills": ["SQL", "Python", "数据分析", "统计学", "假设检验", "回归分析"],
            "optional_skills": ["数据仓库", "数据建模"],
            "embedding": None
        },
        "description": "数据分析师匹配数据分析岗位 - 核心能力匹配"
    },
    # 不匹配对（label=0）
    {
        "id": "MATCH-011",
        "label": 0,
        "resume": {
            "skills": ["React", "Vue", "JavaScript", "CSS3", "HTML5", "Webpack"],
            "implicit_skills": [],
            "skills_with_credibility": [
                {"skill_name": "React", "credibility_score": 0.80},
                {"skill_name": "Vue", "credibility_score": 0.75},
                {"skill_name": "JavaScript", "credibility_score": 0.85},
            ],
            "embedding": None
        },
        "job": {
            "title": "Python后端开发工程师",
            "required_skills": ["Python", "Django", "FastAPI", "MySQL", "Redis", "Docker", "微服务"],
            "optional_skills": ["Go", "高并发"],
            "embedding": None
        },
        "description": "前端工程师匹配后端岗位 - 技能完全不匹配"
    },
    {
        "id": "MATCH-012",
        "label": 0,
        "resume": {
            "skills": ["产品设计", "PRD", "Axure", "Figma", "用户研究", "数据分析"],
            "implicit_skills": [],
            "skills_with_credibility": [
                {"skill_name": "产品设计", "credibility_score": 0.85},
                {"skill_name": "PRD", "credibility_score": 0.80},
                {"skill_name": "数据分析", "credibility_score": 0.70},
            ],
            "embedding": None
        },
        "job": {
            "title": "Java开发工程师",
            "required_skills": ["Java", "Spring Boot", "Spring Cloud", "MySQL", "Redis", "分布式"],
            "optional_skills": ["Go", "Kotlin", "高并发"],
            "embedding": None
        },
        "description": "产品经理匹配Java开发岗位 - 无技术技能交集"
    },
    {
        "id": "MATCH-013",
        "label": 0,
        "resume": {
            "skills": ["市场营销", "品牌策划", "新媒体运营", "内容创作", "数据统计"],
            "implicit_skills": [],
            "skills_with_credibility": [
                {"skill_name": "市场营销", "credibility_score": 0.85},
                {"skill_name": "品牌策划", "credibility_score": 0.80},
                {"skill_name": "内容创作", "credibility_score": 0.75},
            ],
            "embedding": None
        },
        "job": {
            "title": "算法工程师（推荐系统方向）",
            "required_skills": ["Python", "TensorFlow", "PyTorch", "推荐系统", "机器学习", "深度学习", "Hadoop", "Spark"],
            "optional_skills": ["图神经网络", "GNN", "多模态推荐"],
            "embedding": None
        },
        "description": "市场运营人员匹配算法岗位 - 完全不匹配"
    },
    {
        "id": "MATCH-014",
        "label": 0,
        "resume": {
            "skills": ["Python", "数据分析", "SQL", "Excel", "Pandas"],
            "implicit_skills": [],
            "skills_with_credibility": [
                {"skill_name": "Python", "credibility_score": 0.70},
                {"skill_name": "数据分析", "credibility_score": 0.75},
                {"skill_name": "SQL", "credibility_score": 0.80},
            ],
            "embedding": None
        },
        "job": {
            "title": "DevOps/SRE工程师",
            "required_skills": ["Linux", "Docker", "Kubernetes", "Jenkins", "Prometheus", "Grafana", "Terraform", "Ansible", "CI/CD"],
            "optional_skills": ["混合云", "多云"],
            "embedding": None
        },
        "description": "数据分析师匹配DevOps岗位 - 缺少关键运维技能"
    },
    {
        "id": "MATCH-015",
        "label": 0,
        "resume": {
            "skills": ["Java", "Spring", "MySQL", "Redis", "HTML", "CSS", "JavaScript"],
            "implicit_skills": [],
            "skills_with_credibility": [
                {"skill_name": "Java", "credibility_score": 0.80},
                {"skill_name": "Spring", "credibility_score": 0.75},
                {"skill_name": "MySQL", "credibility_score": 0.75},
            ],
            "embedding": None
        },
        "job": {
            "title": "前端架构师",
            "required_skills": ["JavaScript", "TypeScript", "React", "Vue", "Angular", "Webpack", "Node.js", "前端工程化"],
            "optional_skills": ["React Native", "Flutter", "WebAssembly"],
            "embedding": None
        },
        "description": "Java后端工程师匹配前端架构师岗位 - 前端技能严重不足"
    },
    {
        "id": "MATCH-016",
        "label": 0,
        "resume": {
            "skills": ["会计", "财务管理", "Excel", "税务", "审计"],
            "implicit_skills": [],
            "skills_with_credibility": [
                {"skill_name": "会计", "credibility_score": 0.90},
                {"skill_name": "财务管理", "credibility_score": 0.85},
                {"skill_name": "Excel", "credibility_score": 0.80},
            ],
            "embedding": None
        },
        "job": {
            "title": "安全工程师（应用安全方向）",
            "required_skills": ["Web安全", "渗透测试", "Burp Suite", "Nmap", "代码审计", "SDL", "OWASP Top10", "移动安全"],
            "optional_skills": ["CISSP", "零信任"],
            "embedding": None
        },
        "description": "会计人员匹配安全工程师岗位 - 完全不匹配"
    },
    {
        "id": "MATCH-017",
        "label": 0,
        "resume": {
            "skills": ["Python", "数据分析", "SQL", "Tableau", "Excel"],
            "implicit_skills": [],
            "skills_with_credibility": [
                {"skill_name": "Python", "credibility_score": 0.70},
                {"skill_name": "SQL", "credibility_score": 0.75},
                {"skill_name": "Tableau", "credibility_score": 0.70},
            ],
            "embedding": None
        },
        "job": {
            "title": "AI产品经理（AIGC方向）",
            "required_skills": ["SQL", "AIGC", "大模型", "LLM", "产品设计", "数据分析", "机器学习", "深度学习"],
            "optional_skills": ["AI产品", "算法"],
            "embedding": None
        },
        "description": "数据分析师匹配AI产品经理岗位 - 缺少AIGC和产品经验"
    },
    {
        "id": "MATCH-018",
        "label": 0,
        "resume": {
            "skills": ["运维", "Linux", "Shell", "监控", "网络管理", "Windows Server"],
            "implicit_skills": [],
            "skills_with_credibility": [
                {"skill_name": "Linux", "credibility_score": 0.75},
                {"skill_name": "Shell", "credibility_score": 0.70},
                {"skill_name": "网络管理", "credibility_score": 0.80},
            ],
            "embedding": None
        },
        "job": {
            "title": "算法工程师（推荐系统方向）",
            "required_skills": ["Python", "TensorFlow", "PyTorch", "推荐系统", "机器学习", "深度学习", "Hadoop", "Spark"],
            "optional_skills": ["图神经网络", "GNN", "多模态推荐"],
            "embedding": None
        },
        "description": "传统运维工程师匹配算法岗位 - 缺少算法和编程能力"
    },
    {
        "id": "MATCH-019",
        "label": 0,
        "resume": {
            "skills": ["C++", "嵌入式开发", "RTOS", "ARM", "硬件设计"],
            "implicit_skills": [],
            "skills_with_credibility": [
                {"skill_name": "C++", "credibility_score": 0.85},
                {"skill_name": "嵌入式开发", "credibility_score": 0.90},
                {"skill_name": "RTOS", "credibility_score": 0.80},
            ],
            "embedding": None
        },
        "job": {
            "title": "测试开发工程师",
            "required_skills": ["Python", "Java", "Selenium", "Appium", "JMeter", "自动化测试", "性能测试", "接口测试", "CI/CD"],
            "optional_skills": ["安全测试", "AI测试"],
            "embedding": None
        },
        "description": "嵌入式开发工程师匹配测试开发岗位 - 技能方向不一致"
    },
    {
        "id": "MATCH-020",
        "label": 0,
        "resume": {
            "skills": ["Excel", "PPT", "Word", "沟通", "项目管理"],
            "implicit_skills": [],
            "skills_with_credibility": [
                {"skill_name": "Excel", "credibility_score": 0.70},
                {"skill_name": "项目管理", "credibility_score": 0.75},
            ],
            "embedding": None
        },
        "job": {
            "title": "Python后端开发工程师",
            "required_skills": ["Python", "Django", "FastAPI", "MySQL", "Redis", "Docker", "Kubernetes", "微服务"],
            "optional_skills": ["Go", "高并发"],
            "embedding": None
        },
        "description": "行政人员匹配后端开发岗位 - 完全不匹配"
    },
]
