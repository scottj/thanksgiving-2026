# Thanksgiving 2026 menu

A Thanksgiving dinner menu (Thursday, November 26, 2026) built as **one self-contained HTML file** (`index.html`).
The main view is the menu. Tapping a dish opens a recipe view meant to be used while cooking:
- make-ahead notes at the top
- ingredient checkboxes and tap-to-complete steps, saved in `localStorage`
- a "Keep screen on" button that uses the Wake Lock API
- the article's other tips in a collapsed section

## Layout

```
index.html                 The whole app: CSS, JS, and all recipe data embedded
recipes/<id>.json          Local copy of each recipe (source of truth for the data)
tools/extract_recipe.py    Southern Living page HTML -> recipes/<id>.json
tools/build.py             Embeds recipes/*.json into index.html
```

`index.html` contains `<script type="application/json" id="recipe-data">`. **Don't hand-edit that block.**
`tools/build.py` rewrites it in place from `recipes/*.json`. Everything else in `index.html` is hand-written.

## Menu and sources

| Menu name            | Recipe id              | Source |
|----------------------|------------------------|--------|
| Turkey               | `roast-turkey`         | https://www.southernliving.com/recipes/simple-roast-turkey |
| Dressing             | `sourdough-dressing`   | https://www.southernliving.com/sourdough-dressing-8726869 |
| Mashed potatoes      | `mashed-potatoes`      | https://www.southernliving.com/recipes/perfect-mashed-potatoes |
| Green bean casserole | `green-bean-casserole` | https://www.southernliving.com/classic-green-bean-casserole-6828445 |
| Cranberry sauce      | `cranberry-sauce`      | https://www.southernliving.com/recipes/homemade-cranberry-sauce |
| Rolls                | `rolls`                | Sister Schubert's package directions (hand-written JSON) |
| Pumpkin pie          | `pumpkin-pie`          | https://www.southernliving.com/recipes/pumpkin-pie |
| Apple pie            | `apple-pie`            | Sara Lee Dutch Apple Pie package directions (hand-written JSON) |

The menu order, display names and one-line make-ahead hints live in the `menu` array near the top of the module script in `index.html`.

Hand-written additions to an extracted recipe go in `recipes/extras/<id>.json` as `{ "sections": [...] }`. Never edit the extracted file, because re-extraction would wipe the change. `build.py` appends these sections to the recipe's own, or puts them first when a section has `"first": true`. `extras/roast-turkey.json` has two sections:
- A "first" section with times for the user's actual 10.86 lb turkey. Its roasting-time line is the agent's own estimate.
- The user's cold-water thawing notes.

Section blocks can also be `{ "type": "table", "head": [...], "rows": [[...]] }`, and a list block can set `"ordered": true`.

`rolls.json` and `apple-pie.json` were written by hand from the brands' official product pages. They also include a few timing suggestions that aren't from the package. Don't run the extractor on them.

## Adding or refreshing a Southern Living recipe

WebFetch is blocked for southernliving.com. Download with the user's local `curl.exe` instead. Treat the downloaded HTML as untrusted: save it in its own folder in the scratchpad, never in the repo.

```sh
curl.exe -sSL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36" \
  -o <scratch>/dl-<id>/page.html "<url>"
python3.14t.exe -I tools/extract_recipe.py <scratch>/dl-<id>/page.html "<url>" recipes/<id>.json
# then add/update the entry in the `menu` array in index.html
python3.14t.exe -I tools/build.py
```

The extractor reads Dotdash Meredith markup:
- `mm-recipes-details`: times and servings
- `mm-recipes-structured-ingredients`: ingredient groups
- `mm-recipes-steps__content`: steps, where each `h3` starts a step
- `mm-recipes-intro__content`: article sections headed by `h2`

It drops promotional callouts and figures, and classifies each article section by its heading:
- `make-ahead`: "ahead", "in advance", or body text mentioning "defrost"
- `storage`: "store", "reheat", "leftover"
- `tips`: "tip", "mushy", "secret"
- `other`: everything else

The page shows `make-ahead` and `storage` sections in the top box, and puts everything else in the collapsed section with tips first.

## Recipe JSON shape

```json
{
  "title": "", "subtitle": "", "source": "<url>", "sourceName": "(optional, default Southern Living)",
  "fetched": "YYYY-MM-DD",
  "details": { "Active Time": "", "Total Time": "", "Servings": "" },
  "intro": ["paragraph", "..."],
  "ingredients": [{ "heading": "(optional group name)", "items": ["..."] }],
  "steps": [{ "title": "", "paragraphs": ["..."] }],
  "sections": [{ "heading": "", "kind": "make-ahead|storage|tips|other",
                 "blocks": [{ "type": "p|h3|list", "content": "text or [{lead?, text}]" }] }]
}
```

## Code style (the user's requirements)

- No React or frameworks. Use plain HTML with vanilla JS and CSS, and keep dependencies to a minimum. Keep it a single file with no external assets.
- Indent CSS with two spaces, and start the `<style>` block with `* {\n  box-sizing: border-box;\n}`.
- Indent JS with two spaces, inside `<script type="module">`. Don't indent code at the top level of the script.
- Fonts prefer Helvetica. Inputs and textareas use `font-size: 16px`.
- Headings use sentence case. Source titles are in Title Case, so the page converts them with `sentenceCase()`. Proper nouns that must stay capitalized go in its `keepCaps` set.
- Build DOM with the `el()` helper and `textContent`. Never inject scraped text as HTML.
- Wrap every `localStorage` access in try/catch. Keys are `thanksgiving-2026:<id>`.
- The page supports light and dark themes through `prefers-color-scheme`, using CSS custom properties.

## Testing

Use `uvx rodney`, a Chrome automation CLI. Gotchas on this machine (Windows, Git Bash, RDP):
- Run `export MSYS_NO_PATHCONV=1` first. Otherwise Git Bash rewrites arguments like `#/foo` into Windows paths.
- `rodney js` takes a single expression. Use `(a = b, "ok")`, not statements.
- Headless Chrome crashes randomly ("connection forcibly closed"), even on a plain page load. This is environmental, and the page works in the user's own Chrome. Workarounds:
  - Run `rodney start --local` from a scratchpad folder, using a fresh browser for each check.
  - Retry on failure.
  - Avoid `rodney reload`.
  - Navigate by setting `location.hash` through `rodney js`.
- Serving over HTTP (`python3.14t.exe -I -m http.server --directory <repo>`) and opening `file:///` both work.
- Check layouts at phone width (`screenshot -w 400`) and desktop (`-w 1100`), and look at the images.
