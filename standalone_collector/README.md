# 招聘数据采集工具

独立的数据采集程序，用于从多个数据源采集招聘信息。

## 安装

```bash
# 只需要一个依赖
pip install requests
```

## 使用方式

```bash
# 默认采集（Bing + DuckDuckGo）
python collector.py

# 指定数据源
python collector.py --sources bing,duckduckgo

# 指定输出文件
python collector.py --output jobs.json

# 限制关键词数量（只采集前20个关键词）
python collector.py --keywords 20

# 每个关键词采集数量
python collector.py --count 10

# 完整示例
python collector.py --sources bing,duckduckgo --output collected_jobs.json --keywords 50 --count 8
```

## 命令行参数

| 参数 | 默认值 | 说明 |
|-----|-------|------|
| `--sources` | bing,duckduckgo | 数据源，逗号分隔 |
| `--output` | collected_jobs.json | 输出文件路径 |
| `--keywords` | 全部(90+) | 使用前N个关键词 |
| `--count` | 5 | 每个关键词采集数量 |
| `--cookies` | 无 | 登录cookie文件路径(JSON格式) |

## 输出格式

采集完成后，会生成JSON文件，格式如下：

```json
{
  "collected_at": "2026-06-21T18:00:00",
  "total_count": 500,
  "stats": {
    "by_source": {
      "bing": 350,
      "duckduckgo": 150
    }
  },
  "jobs": [
    {
      "job_title": "AI算法工程师",
      "company_name": "某某公司",
      "salary_min": 25,
      "salary_max": 45,
      "location": "北京",
      "skills": [],
      "job_description": "负责机器学习算法研发...",
      "source": "bing_search",
      "source_url": "https://...",
      "collected_at": "2026-06-21T18:00:00"
    }
  ]
}
```

## 支持的数据源

| 数据源 | 名称 | 状态 | 说明 |
|-------|------|------|------|
| `bing` | Bing搜索 | ✅ 可用 | 无需登录，推荐 |
| `duckduckgo` | DuckDuckGo | ✅ 可用 | 无需登录，备用 |
| `zhipin` | BOSS直聘 | 🔧 需配置 | 需要登录cookie |
| `liepin` | 猎聘 | 🔧 需配置 | 需要登录cookie |
| `lagou` | 拉勾 | 🔧 需配置 | 需要登录cookie |

## 采集关键词覆盖

程序内置90+个岗位关键词，覆盖新一代信息技术各领域：

- **人工智能**: AI算法工程师、机器学习工程师、大模型工程师、NLP算法工程师...
- **大数据**: 数据分析师、大数据开发、数据仓库工程师、Flink开发...
- **软件开发**: Java/Python/Go/C++开发、架构师、全栈工程师...
- **前端开发**: React/Vue开发、前端架构师、小程序开发...
- **移动开发**: iOS/Android/Flutter开发...
- **云计算**: 云架构师、DevOps工程师、K8s运维...
- **网络安全**: 渗透测试、安全研究员、安全架构师...
- **区块链**: 智能合约工程师、Web3开发...
- **物联网**: 嵌入式开发、IoT工程师...
- **测试**: 测试开发、自动化测试...
- **产品**: 产品经理、数据产品经理...
- **数据库**: DBA、Redis工程师...

## 将数据导入主系统

采集完成后，将JSON文件发送给主系统管理员，通过以下方式导入：

### 方式1：API导入

```bash
curl -X POST http://主系统地址:8080/api/data/import \
  -H "Content-Type: application/json" \
  -d @collected_jobs.json
```

### 方式2：文件上传

```bash
curl -X POST http://主系统地址:8080/api/data/import/file \
  -F "file=@collected_jobs.json"
```

### 方式3：放到指定目录

将JSON文件放到主系统的 `data/import/` 目录，系统会自动处理。

## 注意事项

1. **采集频率**: 程序已内置请求间隔(0.5秒)，避免被封禁
2. **数据清洗**: 采集的原始数据不需要处理，主系统会自动清洗
3. **技能推断**: 如果采集的数据没有技能字段，主系统会使用LLM自动推断
4. **去重**: 主系统会自动去重，无需手动处理

## 高级配置

### 使用登录cookie

某些数据源需要登录才能访问，创建cookie文件：

```json
// cookies.json
{
  "zhipin": "你的BOSS直聘cookie字符串",
  "liepin": "你的猎聘cookie字符串",
  "lagou": "你的拉勾cookie字符串"
}
```

然后运行：

```bash
python collector.py --sources zhipin,liepin --cookies cookies.json
```

### 获取cookie方法

1. 登录目标网站
2. 打开浏览器开发者工具(F12)
3. 切换到Network标签
4. 刷新页面，找到任意请求
5. 在请求头中找到Cookie字段，复制完整值

## 常见问题

**Q: 采集速度慢怎么办？**
A: 可以减少关键词数量 `--keywords 20`，或减少每个关键词的采集数量 `--count 3`

**Q: 采集到的数据很少？**
A: 检查网络连接，或尝试更换数据源

**Q: 如何验证数据格式是否正确？**
A: 主系统提供了模板接口：GET /api/data/import/template

## 联系方式

如有问题，请联系主系统管理员。
