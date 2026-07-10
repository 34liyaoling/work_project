import requests, re, time, json
from urllib.parse import quote_plus

# Test 1: Direct search with fixed query
print("=== Test 1: Search 'AI算法工程师' ===")
from tools.web_search_tool import WebSearchTool
searcher = WebSearchTool()
searcher.request_delay = 0.5
results = searcher.search_jobs('AI算法工程师', '全国', 5)
if results:
    print(f"Found {len(results)} results")
    for r in results:
        print(f"  - {r['job_title'][:60]}")
        print(f"    source: {r['source']}, is_job_site: {r.get('is_job_site')}")
else:
    print("No results - trying direct Bing...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36',
    }
    url = f'https://www.bing.com/search?q={quote_plus("\"AI算法工程师\" \"招聘\"")}&count=10'
    resp = requests.get(url, headers=headers, timeout=15)
    sections = resp.text.split('class="b_algo"')
    print(f"Found {len(sections)-1} b_algo sections")
    for i, sec in enumerate(sections[1:6], 1):
        h2 = re.search(r'<h2[^>]*>([\s\S]*?)</h2>', sec)
        link = re.search(r'<a[^>]*href="(https?://[^"]*)"', sec)
        if h2:
            t = re.sub(r'<[^>]+>', '', h2.group(1)).strip()
            u = link.group(1) if link else ''
            print(f"  [{i}] {t[:60]}")
            print(f"       {u[:80]}")

# Test 2: Try DuckDuckGo
print("\n=== Test 2: DuckDuckGo search ===")
try:
    ddg_url = f'https://html.duckduckgo.com/html/?q={quote_plus("\"AI算法工程师\" \"招聘\"")}'
    resp = requests.get(ddg_url, headers=headers, timeout=15)
    print(f"Status: {resp.status_code}, Length: {len(resp.text)}")
    sections = resp.text.split('class="result__body"')
    print(f"result__body sections: {len(sections)-1}")
    for i, sec in enumerate(sections[1:6], 1):
        a = re.search(r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([\s\S]*?)</a>', sec)
        if a:
            t = re.sub(r'<[^>]+>', '', a.group(2)).strip()
            print(f"  [{i}] {t[:60]}")
            print(f"       {a.group(1)[:80]}")
except Exception as e:
    print(f"DuckDuckGo failed: {e}")

# Test 3: API endpoint
print("\n=== Test 3: API /api/graph/build ===")
import urllib.request
try:
    req = urllib.request.Request(
        'http://localhost:8000/api/graph/build',
        data=b'{}',
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    r = urllib.request.urlopen(req, timeout=120)
    data = json.loads(r.read())
    print(f"Result: {json.dumps(data, ensure_ascii=False)[:200]}")
except Exception as e:
    print(f"Error: {e}")
