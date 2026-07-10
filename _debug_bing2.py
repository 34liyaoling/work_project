import requests, re
from urllib.parse import quote_plus

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

query = '"AI算法工程师" 招聘 岗位要求'
url = f'https://www.bing.com/search?q={quote_plus(query)}&count=20'
resp = requests.get(url, headers=headers, timeout=15)
print('Status:', resp.status_code)

# Find b_algo sections
parts = resp.text.split('class="b_algo"')
print(f'b_algo sections: {len(parts) - 1}')

if len(parts) > 1:
    for i, part in enumerate(parts[1:6], 1):
        # Extract h2 text
        h2 = re.search(r'<h2[^>]*>([\s\S]*?)</h2>', part)
        if h2:
            clean = re.sub(r'<[^>]+>', '', h2.group(1)).strip()
            print(f'\n  [{i}] {clean[:80]}')
        
        # Extract link
        a = re.search(r'<a[^>]*href="([^"]*)"', part)
        if a:
            print(f'      URL: {a.group(1)[:80]}')

# Also look for #algocore or #b_results
print(f'\nHas b_results: {"b_results" in resp.text}')
print(f'Has #algocore: {"algocore" in resp.text}')
print(f'Has ol#b_results: {"ol id=\"b_results\"" in resp.text}')

# Print section around 5000-10000 chars to see structure
print(f'\n--- HTML around 5000-10000 ---')
section = resp.text[5000:10000]
# Show just the b_algo related parts
for match in re.finditer(r'<h2[^>]*>.*?</h2>', section):
    clean = re.sub(r'<[^>]+>', '', match.group()).strip()
    if clean and len(clean) > 5:
        print(f'  H2: {clean[:80]}')
