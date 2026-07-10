import requests, re
from urllib.parse import quote_plus

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

query = 'AI算法工程师 招聘 全国'
url = f'https://www.bing.com/search?q={quote_plus(query)}&count=20'
resp = requests.get(url, headers=headers, timeout=15)
print('Status:', resp.status_code)

# Try b_algo pattern
results = re.findall(r'<li class="b_algo">[\s\S]*?<a[^>]*href="([^"]*)"[^>]*>([\s\S]*?)</a>', resp.text)
print(f'b_algo pattern: {len(results)} links')

# Try simple a tag extraction
all_links = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>([\s\S]*?)</a>', resp.text)
print(f'Simple pattern: {len(all_links)} total links')

found_jobs = 0
for link, title_html in all_links:
    clean = re.sub(r'<[^>]+>', '', title_html).strip()
    if 5 < len(clean) < 100:
        tl = clean.lower()
        if any(kw in tl for kw in ['招聘','岗位','工程师','开发','算法','架构师']):
            found_jobs += 1
            if found_jobs <= 5:
                print(f'  [{found_jobs}] {clean[:60]}')
print(f'Matched job links: {found_jobs}')
