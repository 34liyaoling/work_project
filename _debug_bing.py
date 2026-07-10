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
print('Content length:', len(resp.text))

# Show some raw HTML to understand the structure
# Look for common patterns
if 'class="b_algo"' in resp.text:
    print('Pattern b_algo: FOUND')
elif 'b_algo' in resp.text:
    print('Pattern b_algo (partial): FOUND')
else:
    print('Pattern b_algo: NOT FOUND')

if 'class="b_caption"' in resp.text:
    print('Pattern b_caption: FOUND')

# Print first 5000 chars
print('\n--- Raw HTML (first 5000 chars) ---')
print(resp.text[:5000])

# Print h2 tags content
h2s = re.findall(r'<h2[^>]*>([\s\S]*?)</h2>', resp.text)
print(f'\nH2 tags: {len(h2s)}')
for h2 in h2s[:10]:
    clean = re.sub(r'<[^>]+>', '', h2).strip()
    if clean:
        print(f'  {clean[:80]}')
