"""Extract a Southern Living recipe page into a clean JSON record.

Usage: python -I tools/extract_recipe.py <page.html> <source-url> <out.json>

The page HTML is untrusted input: it is only parsed as text, never executed.
"""
import html
import json
import re
import sys
from datetime import date

BLOCK_RE = re.compile(
  r'<(h2|h3|p|ul|ol)\b([^>]*)>(.*?)</\1>', re.S
)


def clean(fragment):
  text = re.sub(r'<br\s*/?>', ' ', fragment)
  text = re.sub(r'<[^>]+>', '', text)
  return re.sub(r'\s+', ' ', html.unescape(text)).strip()


def region(src, marker, end_markers):
  """Return the slice of src from the element with class marker up to the first end marker."""
  start = src.find(marker)
  if start < 0:
    return ''
  ends = [src.find(m, start + len(marker)) for m in end_markers]
  ends = [e for e in ends if e > 0]
  return src[start:min(ends) if ends else len(src)]


def list_items(inner):
  items = []
  for li in re.findall(r'<li\b[^>]*>(.*?)</li>', inner, re.S):
    lead = re.match(r'\s*<strong>(.*?)</strong>(.*)', li, re.S)
    if lead:
      items.append({'lead': clean(lead.group(1)), 'text': clean(lead.group(2))})
    else:
      items.append({'text': clean(li)})
  return items


def strip_divs(fragment, class_marker):
  """Remove every <div> whose opening tag contains class_marker, with balanced nesting."""
  open_re = re.compile(r'<div\b[^>]*' + re.escape(class_marker) + r'[^>]*>')
  tag_re = re.compile(r'<(/?)div\b[^>]*>')
  while True:
    m = open_re.search(fragment)
    if not m:
      return fragment
    depth, pos = 1, m.end()
    while depth:
      t = tag_re.search(fragment, pos)
      if not t:
        return fragment[:m.start()]
      depth += -1 if t.group(1) else 1
      pos = t.end()
    fragment = fragment[:m.start()] + fragment[pos:]


def blocks(fragment):
  """Yield (kind, payload) for article content blocks, skipping callouts and ads."""
  # Drop promotional callouts and figure captions entirely.
  fragment = strip_divs(fragment, 'mntl-sc-block-universal-callout')
  fragment = re.sub(r'<figure.*?</figure>', '', fragment, flags=re.S)
  for tag, attrs, inner in BLOCK_RE.findall(fragment):
    if 'mntl-sc-block' not in attrs:
      continue
    if tag in ('ul', 'ol'):
      items = list_items(inner)
      if items:
        yield 'list', items
    else:
      text = clean(inner)
      if text:
        yield tag, text


def section_kind(heading):
  h = heading.lower()
  if 'ahead' in h or 'in advance' in h:
    return 'make-ahead'
  if 'store' in h or 'storing' in h or 'reheat' in h or 'leftover' in h:
    return 'storage'
  if 'tip' in h or 'mushy' in h or 'secret' in h:
    return 'tips'
  return 'other'


def extract(src, url):
  title = re.search(r'<h1[^>]*>(.*?)</h1>', src, re.S)
  subtitle = re.search(r'<p[^>]*article-subheading[^>]*>(.*?)</p>', src, re.S)

  details = {}
  for label, value in re.findall(
    r'mm-recipes-details__label">(.*?)</div>\s*<div class="mm-recipes-details__value">(.*?)</div>',
    src, re.S,
  ):
    details[clean(label).rstrip(':')] = clean(value)

  # Intro article: paragraphs before the first h2, then h2-headed sections.
  intro = []
  sections = []
  intro_src = region(src, 'mm-recipes-intro__content', ['mm-recipes-structured-ingredients'])
  for kind, payload in blocks(intro_src):
    if sections and isinstance(payload, str) and 'defrost' in payload.lower():
      # Thawing guidance is the most time-sensitive prep note there is.
      sections[-1]['kind'] = 'make-ahead'
    if kind == 'h2':
      sections.append({'heading': payload, 'kind': section_kind(payload), 'blocks': []})
    elif payload and isinstance(payload, str) and payload.startswith('Editor'):
      continue
    elif sections:
      sections[-1]['blocks'].append({'type': kind, 'content': payload})
    elif kind == 'p':
      intro.append(payload)

  # Ingredients, grouped by optional sub-headings.
  groups = []
  ing_src = region(src, 'mm-recipes-structured-ingredients"', ['mm-recipes-steps'])
  for m in re.finditer(
    r'<p[^>]*list-heading[^>]*>(.*?)</p>|<li[^>]*list-item[^>]*>(.*?)</li>', ing_src, re.S
  ):
    heading, item = m.groups()
    if heading is not None:
      groups.append({'heading': clean(heading).rstrip(':'), 'items': []})
    else:
      if not groups:
        groups.append({'heading': '', 'items': []})
      groups[-1]['items'].append(clean(item))

  # Steps: each h3 sub-heading starts a step; following paragraphs belong to it.
  steps = []
  steps_src = region(src, 'mm-recipes-steps__content', ['mm-recipes-nutrition', 'mntl-recipe-review', 'article-footer'])
  for kind, payload in blocks(steps_src):
    if kind == 'h3':
      steps.append({'title': payload.rstrip(':'), 'paragraphs': []})
    elif kind == 'p':
      if not steps:
        steps.append({'title': '', 'paragraphs': []})
      steps[-1]['paragraphs'].append(payload)
    elif kind == 'list' and steps:
      steps[-1]['paragraphs'].extend(
        (i.get('lead', '') + ' ' + i['text']).strip() for i in payload
      )

  return {
    'title': clean(title.group(1)) if title else '',
    'subtitle': clean(subtitle.group(1)) if subtitle else '',
    'source': url,
    'fetched': date.today().isoformat(),
    'details': details,
    'intro': intro,
    'ingredients': groups,
    'steps': steps,
    'sections': sections,
  }


def main():
  page, url, out = sys.argv[1:4]
  with open(page, encoding='utf-8') as f:
    src = f.read()
  record = extract(src, url)
  with open(out, 'w', encoding='utf-8', newline='\n') as f:
    json.dump(record, f, ensure_ascii=False, indent=2)
    f.write('\n')
  print(f"{out}: {len(record['ingredients'])} ingredient groups, "
        f"{len(record['steps'])} steps, {len(record['sections'])} sections")


if __name__ == '__main__':
  main()
