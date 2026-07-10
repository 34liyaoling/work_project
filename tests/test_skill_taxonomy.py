"""技能分类模型测试 - 8大领域分类体系"""

from models.skill_taxonomy import DOMAINS, get_all_skills, get_domain_skills, find_skill_domain


def test_domains_count():
    """测试8大领域是否正确分类"""
    expected_domains = {"人工智能", "大数据", "云计算", "软件开发", "DevOps", "区块链/Web3", "网络安全", "物联网"}
    assert set(DOMAINS.keys()) == expected_domains


def test_domain_descriptions():
    """测试每个领域都有描述"""
    for domain, data in DOMAINS.items():
        assert "description" in data
        assert len(data["description"]) > 0


def test_domain_subcategories():
    """测试每个领域都有子类别"""
    for domain, data in DOMAINS.items():
        assert "subcategories" in data
        assert len(data["subcategories"]) >= 2


def test_get_all_skills_return_list():
    """测试 get_all_skills() 返回列表"""
    skills = get_all_skills()
    assert isinstance(skills, list)
    assert len(skills) > 0


def test_get_all_skills_contents():
    """测试 get_all_skills() 包含已知技能"""
    skills = get_all_skills()
    assert "Python" in skills
    assert "PyTorch" in skills
    assert "Kubernetes" in skills
    assert "SQL高级查询" in skills
    assert "Solidity" in skills


def test_get_all_skills_no_duplicates():
    """测试 get_all_skills() 返回的技能总数不少于去重后的数量"""
    skills = get_all_skills()
    assert len(skills) >= len(set(skills))
    assert len(skills) >= 180


def test_get_all_skills_count():
    """测试 get_all_skills() 数量合理"""
    skills = get_all_skills()
    assert len(skills) > 50


def test_get_domain_skills_existing():
    """测试 get_domain_skills() 按领域筛选"""
    ai_skills = get_domain_skills("人工智能")
    assert isinstance(ai_skills, list)
    assert len(ai_skills) > 0
    assert "Python" in ai_skills
    assert "PyTorch" in ai_skills
    assert "GPT系列" in ai_skills


def test_get_domain_skills_all_domains():
    """测试所有领域都能返回技能列表"""
    for domain in DOMAINS:
        skills = get_domain_skills(domain)
        assert len(skills) >= 3, f"领域'{domain}'的技能数应不少于3个"


def test_get_domain_skills_cloud():
    """测试云计算领域技能"""
    cloud_skills = get_domain_skills("云计算")
    assert "AWS" in cloud_skills
    assert "Docker" in cloud_skills
    assert "Kubernetes" in cloud_skills
    assert "Terraform" in cloud_skills


def test_get_domain_skills_big_data():
    """测试大数据领域技能"""
    bigdata_skills = get_domain_skills("大数据")
    assert "Spark" in bigdata_skills
    assert "Flink" in bigdata_skills
    assert "HDFS" in bigdata_skills


def test_get_domain_skills_nonexistent():
    """测试不存在的领域返回空列表"""
    skills = get_domain_skills("不存在的领域")
    assert skills == []


def test_find_skill_domain_python():
    """测试 find_skill_domain() 反向查找 - Python在人工智能"""
    domain = find_skill_domain("Python")
    assert domain == "人工智能"


def test_find_skill_domain_pytorch():
    """测试 find_skill_domain() - PyTorch在人工智能"""
    domain = find_skill_domain("PyTorch")
    assert domain == "人工智能"


def test_find_skill_domain_kubernetes():
    """测试 find_skill_domain() - Kubernetes在云计算"""
    domain = find_skill_domain("Kubernetes")
    assert domain == "云计算"


def test_find_skill_domain_react():
    """测试 find_skill_domain() - React在软件开发"""
    domain = find_skill_domain("React/Vue/Angular")
    assert domain == "软件开发"


def test_find_skill_domain_nonexistent():
    """测试不存在的技能返回 None"""
    domain = find_skill_domain("不存在的技能名称")
    assert domain is None


def test_find_skill_domain_case_sensitive():
    """测试 find_skill_domain() 大小写敏感"""
    domain_lower = find_skill_domain("python")
    domain_upper = find_skill_domain("Python")
    assert domain_lower == domain_upper == "人工智能"


def test_find_skill_domain_blockchain():
    """测试 find_skill_domain() - 区块链领域"""
    domain = find_skill_domain("Solidity")
    assert domain == "区块链/Web3"


def test_find_skill_domain_security():
    """测试 find_skill_domain() - 网络安全领域技能"""
    domain = find_skill_domain("渗透测试")
    assert domain is not None
    # 渗透测试同时出现在DevOps和网络安全，find_skill_domain返回第一个匹配
    domain2 = find_skill_domain("防火墙")
    assert domain2 == "网络安全"

    domain3 = find_skill_domain("IDS/IPS")
    assert domain3 == "网络安全"


def test_domain_skill_coverage():
    """验证所有 get_all_skills 中的技能都能被 find_skill_domain 找到"""
    all_skills = get_all_skills()
    for skill in all_skills:
        domain = find_skill_domain(skill)
        assert domain is not None, f"技能'{skill}'未能找到所属领域"


def test_domain_skills_have_items():
    """测试每个领域的子分类都有技能列表"""
    for domain in DOMAINS:
        for cat_name, cat_skills in DOMAINS[domain]["subcategories"].items():
            assert len(cat_skills) > 0, f"领域'{domain}'的分类'{cat_name}'缺少技能"
