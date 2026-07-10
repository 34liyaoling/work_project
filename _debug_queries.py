import requests, re
from urllib.parse import quote_plus

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# Try with different, more specific queries
queries = [
    '"AI算法工程师" 岗位要求',
    '"算法工程师" 招聘 JD',
    '"AI算法工程师" "招聘"',
]

for q in queries:
    url = f'https://www.bing.com/search?q={quote_plus(q)}&count=10'
    resp = requests.get(url, headers=headers, timeout=15)
    parts = resp.text.split('class="b_algo"')
    
    job_count = 0
    for part in parts[1:]:
        h2 = re.search(r'<h2[^>]*>([\s\S]*?)</h2>', part)
        if h2:
            clean = re.sub(r'<[^>]+>', '', h2.group(1)).strip()
            a = re.search(r'<a[^>]*href="([^"]*)"', part)
            url_str = a.group(1) if a else ''
            if any(kw in clean.lower() for kw in ['招聘','岗位','工程师','开发','算法']):
                job_count += 1
                if job_count <= 3:
                    print(f'  [{job_count}] {clean[:60]}')
                    print(f'      {url_str[:80]}')
    print(f'Query "{q[:20]}": {len(parts)-1} sections, {job_count} job-related')
    print()
