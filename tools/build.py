"""Embed recipes/*.json into index.html so the page stays a single self-contained file.

Usage: python -I tools/build.py
Replaces the contents of <script type="application/json" id="recipe-data"> in place.
"""
import json
import pathlib
import re

root = pathlib.Path(__file__).resolve().parent.parent
recipes = {}
for path in sorted((root / 'recipes').glob('*.json')):
  recipes[path.stem] = json.loads(path.read_text(encoding='utf-8'))

payload = json.dumps(recipes, ensure_ascii=False, indent=2).replace('</', '<\\/')
page_path = root / 'index.html'
page = page_path.read_text(encoding='utf-8')
pattern = re.compile(
  r'(<script type="application/json" id="recipe-data">)(.*?)(</script>)', re.S
)
if not pattern.search(page):
  raise SystemExit('recipe-data script tag not found in index.html')
page = pattern.sub(lambda m: m.group(1) + '\n' + payload + '\n' + m.group(3), page, count=1)
page_path.write_text(page, encoding='utf-8', newline='\n')
print(f'Embedded {len(recipes)} recipes: {", ".join(recipes)}')
