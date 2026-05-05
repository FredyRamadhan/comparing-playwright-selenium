import pytest
import os
import json
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
NC_USER  = os.getenv("NC_USER", "admin")
NC_PASS  = os.getenv("NC_PASS", "admin123")

@pytest.fixture(scope="session")
def nc_browser():
    """Browser session sekali untuk semua test."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context()

        # Login sekali di awal session
        page = context.new_page()
        page.goto(f"{BASE_URL}/login")
        page.wait_for_selector('input[name="user"]', timeout=30000)
        page.fill('input[name="user"]', NC_USER)
        page.fill('input[name="password"]', NC_PASS)
        page.click('button[type="submit"]')
        page.wait_for_url("**/apps/**", timeout=30000)
        page.close()

        yield context

        browser.close()

@pytest.fixture
def nc_page(nc_browser):
    """Halaman baru dari session yang sudah login."""
    p = nc_browser.new_page()
    yield p
    p.close()

@pytest.fixture
def nc_logged_in(nc_browser):
    """Halaman baru, langsung ke files (sudah login via session)."""
    p = nc_browser.new_page()
    p.goto(f"{BASE_URL}/apps/files")
    p.wait_for_load_state("networkidle")
    yield p
    p.close()


# ── JSON report plugin ────────────────────────────────────────────────────────

_report_data = {
    "generated_at": "",
    "duration": 0,
    "results": []
}
_session_start = None

def pytest_sessionstart(session):
    global _session_start
    _session_start = time.time()

def pytest_runtest_logreport(report):
    if report.when == "call" or (report.when == "setup" and report.failed):
        node = report.nodeid                        # e.g. tests/test_nav.py::Class::test_foo
        parts = node.split("::")
        filename = parts[0].replace("tests/", "").replace("tests\\", "")
        test_name = parts[-1]

        if report.passed:
            outcome = "passed"
        elif report.failed:
            outcome = "failed"
        else:
            outcome = "skipped"

        error_msg = ""
        if report.failed and report.longrepr:
            error_msg = str(report.longrepr)

        _report_data["results"].append({
            "filename": filename,
            "test_name": test_name,
            "nodeid": node,
            "outcome": outcome,
            "duration": round(getattr(report, "duration", 0), 2),
            "error": error_msg,
        })

def pytest_sessionfinish(session, exitstatus):
    import datetime
    _report_data["generated_at"] = datetime.datetime.now().strftime("%d. %m. %Y %H:%M:%S")
    _report_data["duration"] = round(time.time() - _session_start, 1)

    os.makedirs("reports", exist_ok=True)
    with open("reports/report_data.json", "w", encoding="utf-8") as f:
        json.dump(_report_data, f, indent=2, ensure_ascii=False)

    # Generate HTML dari template
    _generate_html("reports/report_data.json", "reports/report.html")
    print("\n📊 HTML Report: reports/report.html")


def _generate_html(json_path, html_path):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    results = data["results"]
    total    = len(results)
    passed   = sum(1 for r in results if r["outcome"] == "passed")
    failed   = sum(1 for r in results if r["outcome"] == "failed")
    skipped  = sum(1 for r in results if r["outcome"] == "skipped")

    # Group by filename
    files = {}
    for r in results:
        files.setdefault(r["filename"], []).append(r)

    rows_html = ""
    for fname, tests in files.items():
        rows_html += f"""
        <div class="file-group">
          <div class="file-header" onclick="toggleGroup(this)">
            <span class="chevron">▼</span>
            <span class="filename">{fname}</span>
          </div>
          <div class="file-body">
        """
        for t in tests:
            outcome = t["outcome"]
            icon = "✓" if outcome == "passed" else ("✕" if outcome == "failed" else "–")
            icon_cls = outcome
            dur = f"{t['duration']}s"
            name_display = t["test_name"].replace("_", " ")
            error_block = ""
            if t.get("error"):
                short_err = t["error"].split("AssertionError:")[-1].strip().split("\n")[0][:200]
                error_block = f'<div class="error-msg">{short_err}</div>'

            rows_html += f"""
            <div class="test-row {outcome}">
              <div class="test-left">
                <span class="icon {icon_cls}">{icon}</span>
                <div class="test-info">
                  <span class="test-name">{name_display}</span>
                  <span class="test-node">{t['nodeid']}</span>
                  {error_block}
                </div>
              </div>
              <span class="duration">{dur}</span>
            </div>
            """
        rows_html += "</div></div>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Test Report — Nextcloud</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg: #f8f9fb;
    --surface: #ffffff;
    --border: #e4e7ec;
    --text: #111827;
    --text-muted: #6b7280;
    --passed: #16a34a;
    --passed-bg: #f0fdf4;
    --passed-border: #bbf7d0;
    --failed: #dc2626;
    --failed-bg: #fef2f2;
    --failed-border: #fecaca;
    --skipped: #9333ea;
    --skipped-bg: #faf5ff;
    --skipped-border: #e9d5ff;
    --file-header-bg: #f1f5f9;
    --radius: 8px;
  }}

  body {{
    font-family: 'IBM Plex Sans', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 32px 24px;
  }}

  .container {{ max-width: 1000px; margin: 0 auto; }}

  /* ── Header ── */
  .header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 12px;
  }}
  .header-title {{
    font-size: 20px;
    font-weight: 600;
    color: var(--text);
    font-family: 'IBM Plex Mono', monospace;
  }}
  .header-meta {{
    font-size: 13px;
    color: var(--text-muted);
    font-family: 'IBM Plex Mono', monospace;
  }}

  /* ── Filter bar ── */
  .filter-bar {{
    display: flex;
    align-items: center;
    gap: 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,.06);
  }}

  .search-wrap {{
    flex: 1;
    display: flex;
    align-items: center;
    padding: 0 14px;
    border-right: 1px solid var(--border);
  }}
  .search-wrap svg {{ color: var(--text-muted); margin-right: 8px; flex-shrink:0; }}
  .search-wrap input {{
    border: none; outline: none;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 14px;
    color: var(--text);
    background: transparent;
    width: 100%;
    padding: 12px 0;
  }}

  .filter-btn {{
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 12px 18px;
    border: none;
    background: transparent;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-muted);
    cursor: pointer;
    border-left: 1px solid var(--border);
    transition: background .15s, color .15s;
    white-space: nowrap;
  }}
  .filter-btn:first-child {{ border-left: none; }}
  .filter-btn .count {{
    font-weight: 600;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
  }}
  .filter-btn:hover {{ background: var(--file-header-bg); color: var(--text); }}
  .filter-btn.active {{ background: var(--text); color: #fff; }}
  .filter-btn.active.passed {{ background: var(--passed); }}
  .filter-btn.active.failed {{ background: var(--failed); }}
  .filter-btn.active.skipped {{ background: var(--skipped); }}

  /* ── File groups ── */
  .file-group {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,.05);
  }}

  .file-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    background: var(--file-header-bg);
    cursor: pointer;
    user-select: none;
    border-bottom: 1px solid var(--border);
  }}
  .file-header:hover {{ background: #e8edf3; }}
  .chevron {{ font-size: 11px; color: var(--text-muted); transition: transform .2s; }}
  .file-header.collapsed .chevron {{ transform: rotate(-90deg); }}
  .filename {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
  }}

  .file-body.collapsed {{ display: none; }}

  /* ── Test rows ── */
  .test-row {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    transition: background .12s;
  }}
  .test-row:last-child {{ border-bottom: none; }}
  .test-row:hover {{ background: #fafbfc; }}

  .test-left {{ display: flex; align-items: flex-start; gap: 12px; flex: 1; min-width: 0; }}

  .icon {{
    width: 22px; height: 22px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px;
    font-weight: 700;
    flex-shrink: 0;
    margin-top: 1px;
  }}
  .icon.passed {{ background: var(--passed-bg); color: var(--passed); border: 1.5px solid var(--passed-border); }}
  .icon.failed  {{ background: var(--failed-bg);  color: var(--failed);  border: 1.5px solid var(--failed-border); }}
  .icon.skipped {{ background: var(--skipped-bg); color: var(--skipped); border: 1.5px solid var(--skipped-border); }}

  .test-info {{ display: flex; flex-direction: column; gap: 2px; min-width: 0; }}
  .test-name {{ font-size: 14px; font-weight: 500; color: var(--text); }}
  .test-node {{ font-size: 11px; color: var(--text-muted); font-family: 'IBM Plex Mono', monospace; }}
  .error-msg {{
    margin-top: 6px;
    font-size: 12px;
    color: var(--failed);
    font-family: 'IBM Plex Mono', monospace;
    background: var(--failed-bg);
    border: 1px solid var(--failed-border);
    border-radius: 4px;
    padding: 6px 10px;
    white-space: pre-wrap;
    word-break: break-word;
  }}

  .duration {{
    font-size: 13px;
    color: var(--text-muted);
    font-family: 'IBM Plex Mono', monospace;
    flex-shrink: 0;
    margin-left: 16px;
    padding-top: 2px;
  }}

  /* ── Hidden rows (filter) ── */
  .test-row.hidden {{ display: none; }}
  .file-group.hidden {{ display: none; }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <span class="header-title">Nextcloud · Test Report</span>
    <span class="header-meta">{data['generated_at']} &nbsp;·&nbsp; Total time: {data['duration']}s</span>
  </div>

  <div class="filter-bar">
    <div class="search-wrap">
      <svg width="15" height="15" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="9" cy="9" r="6"/><path d="M15 15l3 3"/>
      </svg>
      <input type="text" id="searchInput" placeholder="Search tests…" oninput="applyFilters()">
    </div>
    <button class="filter-btn active" id="btn-all" onclick="setFilter('all')">
      All <span class="count">{total}</span>
    </button>
    <button class="filter-btn" id="btn-passed" onclick="setFilter('passed')">
      Passed <span class="count">{passed}</span>
    </button>
    <button class="filter-btn" id="btn-failed" onclick="setFilter('failed')">
      Failed <span class="count">{failed}</span>
    </button>
    <button class="filter-btn" id="btn-skipped" onclick="setFilter('skipped')">
      Skipped <span class="count">{skipped}</span>
    </button>
  </div>

  <div id="testList">
    {rows_html}
  </div>

</div>
<script>
  let currentFilter = 'all';

  function setFilter(f) {{
    currentFilter = f;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active','passed','failed','skipped'));
    const btn = document.getElementById('btn-' + f);
    btn.classList.add('active');
    if (f !== 'all') btn.classList.add(f);
    applyFilters();
  }}

  function applyFilters() {{
    const q = document.getElementById('searchInput').value.toLowerCase();
    document.querySelectorAll('.file-group').forEach(group => {{
      let anyVisible = false;
      group.querySelectorAll('.test-row').forEach(row => {{
        const name = row.querySelector('.test-name').textContent.toLowerCase();
        const node = row.querySelector('.test-node').textContent.toLowerCase();
        const matchFilter = currentFilter === 'all' || row.classList.contains(currentFilter);
        const matchSearch = !q || name.includes(q) || node.includes(q);
        if (matchFilter && matchSearch) {{
          row.classList.remove('hidden');
          anyVisible = true;
        }} else {{
          row.classList.add('hidden');
        }}
      }});
      group.classList.toggle('hidden', !anyVisible);
    }});
  }}

  function toggleGroup(header) {{
    header.classList.toggle('collapsed');
    header.nextElementSibling.classList.toggle('collapsed');
  }}
</script>
</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)