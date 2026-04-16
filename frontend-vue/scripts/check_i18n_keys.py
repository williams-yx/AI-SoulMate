import re
from pathlib import Path

root = Path('.')
locale_file = root / 'src' / 'locales' / 'index.ts'

# gather used keys
used_asset = set()
used_product = set()
for p in (root / 'src').rglob('*'):
    if p.suffix.lower() in {'.vue', '.ts', '.js'}:
        try:
            text = p.read_text(encoding='utf-8')
        except Exception:
            continue
        for m in re.finditer(r"t\(\s*['\"]assetDetail\.([a-zA-Z0-9_]+)['\"]\s*\)", text):
            used_asset.add(m.group(1))
        for m in re.finditer(r"t\(\s*['\"]productDetail\.([a-zA-Z0-9_]+)['\"]\s*\)", text):
            used_product.add(m.group(1))
        # also detect keys referenced via string assignment like 'assetDetail.xxx'
        for m in re.finditer(r"['\"]assetDetail\.([a-zA-Z0-9_]+)['\"]", text):
            used_asset.add(m.group(1))
        for m in re.finditer(r"['\"]productDetail\.([a-zA-Z0-9_]+)['\"]", text):
            used_product.add(m.group(1))

# parse locale file to extract keys under assetDetail and productDetail for both locales
content = ''
try:
    content = locale_file.read_text(encoding='utf-8')
except FileNotFoundError:
    print('Locale file not found:', locale_file)
    raise


def extract_block_keys(content, block_name):
    keys = set()
    idx = 0
    while True:
        m = re.search(rf"{block_name}\s*:\s*{{", content[idx:])
        if not m:
            break
        start = idx + m.end()-1
        i = start
        depth = 0
        in_s = None
        escape = False
        while i < len(content):
            ch = content[i]
            if in_s:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == in_s:
                    in_s = None
            else:
                if ch == '"' or ch == "'":
                    in_s = ch
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            i += 1
        else:
            break
        block = content[start+1:end]
        # find top-level keys
        depth = 0
        in_s = None
        escape = False
        key_buf = ''
        collecting = False
        for line in block.split('\n'):
            lm = re.match(r"\s*([a-zA-Z0-9_]+)\s*:\s*", line)
            if lm:
                keys.add(lm.group(1))
        idx = end
    return keys

asset_keys_zh = set()
product_keys_zh = set()
asset_keys_en = set()
product_keys_en = set()

m_zh = re.search(r"['\"]zh-CN['\"]\s*:\s*{", content)
if m_zh:
    start = m_zh.end()-1
    i = start
    depth = 0
    in_s = None
    escape = False
    while i < len(content):
        ch = content[i]
        if in_s:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == in_s:
                in_s = None
        else:
            if ch == '"' or ch == "'":
                in_s = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        i += 1
    zh_block = content[start+1:end]
    asset_keys_zh = extract_block_keys(zh_block, 'assetDetail')
    product_keys_zh = extract_block_keys(zh_block, 'productDetail')

m_en = re.search(r"['\"]en-US['\"]\s*:\s*{", content)
if m_en:
    start = m_en.end()-1
    i = start
    depth = 0
    in_s = None
    escape = False
    while i < len(content):
        ch = content[i]
        if in_s:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == in_s:
                in_s = None
        else:
            if ch == '"' or ch == "'":
                in_s = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        i += 1
    en_block = content[start+1:end]
    asset_keys_en = extract_block_keys(en_block, 'assetDetail')
    product_keys_en = extract_block_keys(en_block, 'productDetail')

# compute missing
missing_asset_zh = sorted(used_asset - asset_keys_zh)
missing_asset_en = sorted(used_asset - asset_keys_en)
missing_product_zh = sorted(used_product - product_keys_zh)
missing_product_en = sorted(used_product - product_keys_en)

print('used_asset_count=', len(used_asset))
print('used_product_count=', len(used_product))
print('\nMissing asset keys in zh-CN (count={}):'.format(len(missing_asset_zh)))
for k in missing_asset_zh:
    print(k)
print('\nMissing asset keys in en-US (count={}):'.format(len(missing_asset_en)))
for k in missing_asset_en:
    print(k)
print('\nMissing product keys in zh-CN (count={}):'.format(len(missing_product_zh)))
for k in missing_product_zh:
    print(k)
print('\nMissing product keys in en-US (count={}):'.format(len(missing_product_en)))
for k in missing_product_en:
    print(k)
