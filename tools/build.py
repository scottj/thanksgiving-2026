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

# Hand-written additions live in recipes/extras/<id>.json so re-extracting a
# recipe never wipes them. Their sections are appended to the recipe's own.
for path in sorted((root / 'recipes' / 'extras').glob('*.json')):
  if path.stem not in recipes:
    raise SystemExit(f'{path.name}: no recipes/{path.name} to extend')
  extra = json.loads(path.read_text(encoding='utf-8'))
  # "subtitle" / "ingredients" / "steps" in an extras file replace the extracted ones outright.
  for key in ('subtitle', 'ingredients', 'steps'):
    if key in extra:
      recipes[path.stem][key] = extra[key]
  sections = recipes[path.stem]['sections']
  for section in extra.get('sections', []):
    # "first": true puts a section ahead of the extracted ones.
    if section.pop('first', False):
      sections.insert(sum(1 for s in sections if s.get('pinned')), dict(section, pinned=True))
    else:
      sections.append(section)

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
