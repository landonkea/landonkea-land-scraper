"""report.py - Generates a static HTML report for Cloudflare Pages hosting."""

import json  # converts Python data to JSON for embedding in the HTML file
from datetime import datetime  # timestamps the report so you know when it was last updated


def generate_report(conn):
    """Builds a single-file HTML dashboard from the SQLite database."""
    # Fetch all listings sorted by price ascending
    rows = conn.execute(
        'SELECT score, price, title, url, location, source FROM lands ORDER BY price ASC'
    ).fetchall()

    # Convert rows to list of dicts for easy JSON embedding
    listings = []
    for score, price, title, url, location, source in rows:
        listings.append({
            'score': score,
            'price': price,
            'title': title,
            'url': url,
            'location': location or '',
            'source': source,
        })

    # Get unique sources for the filter checkboxes
    sources = sorted(set(r[5] for r in rows))

    # Get stats
    total = len(rows)
    good = sum(1 for r in rows if r[0] >= 50)
    cheapest = f'${rows[0][1]:,.0f}' if rows else 'N/A'
    best_score = max((r[0] for r in rows), default=0)

    # Timestamp
    updated = datetime.now().strftime('%m/%d/%Y %I:%M %p')

    # Embed listings as JSON inside the HTML
    listings_json = json.dumps(listings)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Arizona Land Deals</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; background: #0f1117; color: #e0e0e0; min-height: 100vh; }}
.header {{ background: #1a1d27; border-bottom: 1px solid #2a2d3a; padding: 20px 24px; position: sticky; top: 0; z-index: 100; }}
.header h1 {{ font-size: 22px; font-weight: 600; color: #fff; margin-bottom: 4px; }}
.header .subtitle {{ font-size: 13px; color: #888; }}
.stats {{ display: flex; gap: 24px; margin-top: 12px; flex-wrap: wrap; }}
.stat {{ background: #1e2130; border: 1px solid #2a2d3a; border-radius: 8px; padding: 10px 16px; min-width: 120px; }}
.stat .label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }}
.stat .value {{ font-size: 20px; font-weight: 700; color: #4ade80; margin-top: 2px; }}
.stat .value.blue {{ color: #60a5fa; }}
.stat .value.yellow {{ color: #facc15; }}
.controls {{ background: #14161f; border-bottom: 1px solid #2a2d3a; padding: 16px 24px; display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }}
.search {{ flex: 1; min-width: 200px; padding: 10px 14px; background: #1e2130; border: 1px solid #2a2d3a; border-radius: 8px; color: #e0e0e0; font-size: 14px; outline: none; }}
.search:focus {{ border-color: #4ade80; }}
.filter-group {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
.filter-group label {{ font-size: 12px; color: #888; white-space: nowrap; }}
.filter-input {{ width: 90px; padding: 8px 10px; background: #1e2130; border: 1px solid #2a2d3a; border-radius: 6px; color: #e0e0e0; font-size: 13px; outline: none; }}
.filter-input:focus {{ border-color: #4ade80; }}
select {{ padding: 8px 10px; background: #1e2130; border: 1px solid #2a2d3a; border-radius: 6px; color: #e0e0e0; font-size: 13px; outline: none; cursor: pointer; }}
.count {{ font-size: 13px; color: #888; padding: 8px 0; white-space: nowrap; }}
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th {{ background: #1a1d27; padding: 12px 16px; text-align: left; font-weight: 600; font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; cursor: pointer; user-select: none; white-space: nowrap; position: sticky; top: 0; border-bottom: 2px solid #2a2d3a; }}
th:hover {{ color: #4ade80; }}
th .arrow {{ margin-left: 4px; font-size: 10px; }}
td {{ padding: 12px 16px; border-bottom: 1px solid #1e2130; vertical-align: top; }}
tr:hover {{ background: #1a1d27; }}
.score {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 13px; }}
.score.high {{ background: #166534; color: #4ade80; }}
.score.mid {{ background: #713f12; color: #facc15; }}
.score.low {{ background: #7c2d12; color: #fb923c; }}
.price {{ font-weight: 700; color: #4ade80; white-space: nowrap; }}
.title-cell a {{ color: #e0e0e0; text-decoration: none; }}
.title-cell a:hover {{ color: #4ade80; text-decoration: underline; }}
.source {{ color: #60a5fa; font-size: 13px; }}
.location {{ color: #aaa; font-size: 13px; }}
.no-results {{ text-align: center; padding: 60px 20px; color: #666; font-size: 16px; }}
@media (max-width: 768px) {{
  .controls {{ flex-direction: column; }}
  .search {{ min-width: 100%; }}
  .filter-group {{ width: 100%; }}
  .stats {{ gap: 8px; }}
  .stat {{ min-width: 100px; padding: 8px 12px; }}
  th, td {{ padding: 8px 10px; font-size: 13px; }}
}}
</style>
</head>
<body>
<div class="header">
  <h1>Arizona Land Deals</h1>
  <div class="subtitle">Last updated: {updated}</div>
  <div class="stats">
    <div class="stat"><div class="label">Total</div><div class="value blue">{total}</div></div>
    <div class="stat"><div class="label">Good (50+)</div><div class="value">{good}</div></div>
    <div class="stat"><div class="label">Cheapest</div><div class="value yellow">{cheapest}</div></div>
    <div class="stat"><div class="label">Best Score</div><div class="value">{best_score}</div></div>
  </div>
</div>
<div class="controls">
  <input type="text" class="search" id="search" placeholder="Search listings...">
  <div class="filter-group">
    <label>Min $</label><input type="number" class="filter-input" id="minPrice" placeholder="0">
    <label>Max $</label><input type="number" class="filter-input" id="maxPrice" placeholder="100000">
  </div>
  <div class="filter-group">
    <label>Min Score</label><input type="number" class="filter-input" id="minScore" placeholder="0" min="0" max="100">
  </div>
  <div class="filter-group">
    <label>Source</label>
    <select id="sourceFilter">
      <option value="">All Sources</option>
      {''.join(f'<option value="{s}">{s}</option>' for s in sources)}
    </select>
  </div>
  <div class="count" id="count">{total} listings</div>
</div>
<div class="table-wrap">
<table>
<thead>
<tr>
  <th data-sort="score">Score <span class="arrow"></span></th>
  <th data-sort="price">Price <span class="arrow"></span></th>
  <th data-sort="title">Title <span class="arrow"></span></th>
  <th data-sort="source">Source <span class="arrow"></span></th>
  <th data-sort="location">Location <span class="arrow"></span></th>
</tr>
</thead>
<tbody id="tbody"></tbody>
</table>
<div class="no-results" id="noResults" style="display:none;">No listings match your filters.</div>
</div>

<script>
const DATA = {listings_json};
let sortKey = 'price';
let sortAsc = true;

function scoreClass(s) {{ return s >= 70 ? 'high' : s >= 50 ? 'mid' : 'low'; }}

function render() {{
  const q = document.getElementById('search').value.toLowerCase();
  const minP = parseFloat(document.getElementById('minPrice').value) || 0;
  const maxP = parseFloat(document.getElementById('maxPrice').value) || Infinity;
  const minS = parseInt(document.getElementById('minScore').value) || 0;
  const src = document.getElementById('sourceFilter').value;

  let filtered = DATA.filter(r => {{
    if (r.price < minP || r.price > maxP) return false;
    if (r.score < minS) return false;
    if (src && r.source !== src) return false;
    if (q) {{
      const text = (r.title + r.location + r.source).toLowerCase();
      if (!text.includes(q)) return false;
    }}
    return true;
  }});

  filtered.sort((a, b) => {{
    let va = a[sortKey], vb = b[sortKey];
    if (typeof va === 'string') {{ va = va.toLowerCase(); vb = vb.toLowerCase(); }}
    if (va < vb) return sortAsc ? -1 : 1;
    if (va > vb) return sortAsc ? 1 : -1;
    return 0;
  }});

  const tbody = document.getElementById('tbody');
  tbody.innerHTML = filtered.map(r => `<tr>
    <td><span class="score ${{scoreClass(r.score)}}">${{r.score}}</span></td>
    <td class="price">$${{r.price.toLocaleString()}}</td>
    <td class="title-cell"><a href="${{r.url}}" target="_blank" rel="noopener">${{r.title}}</a></td>
    <td class="source">${{r.source}}</td>
    <td class="location">${{r.location}}</td>
  </tr>`).join('');

  document.getElementById('count').textContent = filtered.length + ' listings';
  document.getElementById('noResults').style.display = filtered.length ? 'none' : 'block';

  // Update sort arrows
  document.querySelectorAll('th').forEach(th => {{
    const key = th.dataset.sort;
    const arrow = th.querySelector('.arrow');
    if (key === sortKey) arrow.textContent = sortAsc ? '\\u25B2' : '\\u25BC';
    else arrow.textContent = '';
  }});
}}

// Sort on column click
document.querySelectorAll('th[data-sort]').forEach(th => {{
  th.addEventListener('click', () => {{
    const key = th.dataset.sort;
    if (sortKey === key) sortAsc = !sortAsc;
    else {{ sortKey = key; sortAsc = true; }}
    render();
  }});
}});

// Re-render on any filter change
['search', 'minPrice', 'maxPrice', 'minScore', 'sourceFilter'].forEach(id => {{
  document.getElementById(id).addEventListener('input', render);
  document.getElementById(id).addEventListener('change', render);
}});

render();
</script>
</body>
</html>"""

    path = 'docs/index.html'  # output path for the static site
    import os  # needed to create the directory if it doesn't exist
    os.makedirs('docs', exist_ok=True)  # create the docs folder
    with open(path, 'w') as f:  # write the HTML to disk
        f.write(html)  # dump the entire report as one file
    return path  # return the file path so the caller knows where it is
