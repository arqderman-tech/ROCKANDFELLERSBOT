"""
generar_web.py - RFBOT
Genera docs/index.html con:
  - Tab global (todos los locales)
  - Tab por local: Orono / Alto Rosario / Savoy
  - Sub-tabs por carta: Restaurante / Cafetería / Vinos y Espumantes / Cocktails
  - Comparativo de precios entre locales
  - Rankings con filtro por local/carta
"""

import json
from pathlib import Path
from datetime import datetime

DIR_DATA = Path("data")
DIR_DOCS = Path("docs")

LOCALES = ["Orono", "Alto Rosario", "Savoy"]
CARTAS = {
    "restaurante": "Restaurante",
    "cafeteria": "Cafetería",
    "vinos-y-espumantes": "Vinos y Espumantes",
    "cocktails": "Cocktails"
}
CARTA_EMOJIS = {
    "restaurante": "🍽️",
    "cafeteria": "☕",
    "vinos-y-espumantes": "🍷",
    "cocktails": "🍸"
}
LOCAL_EMOJIS = {
    "Orono": "🎸",
    "Alto Rosario": "🏬",
    "Savoy": "✨"
}

def leer_json(nombre):
    ruta = DIR_DATA / nombre
    if ruta.exists():
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    return None

def fmt_pct(v):
    if v is None: return "—"
    signo = "+" if v > 0 else ""
    return f"{signo}{v:.2f}%"

def color_pct(v):
    if v is None: return "#888"
    if v > 0: return "#ef4444"
    if v < 0: return "#22c55e"
    return "#888"

def main():
    DIR_DOCS.mkdir(exist_ok=True)

    resumen     = leer_json("resumen.json") or {}
    graficos    = leer_json("graficos.json") or {}
    rank_dia    = leer_json("ranking_dia.json") or []
    rank_7d     = leer_json("ranking_7d.json") or []
    rank_mes    = leer_json("ranking_mes.json") or []
    rank_local  = leer_json("ranking_por_local.json") or {}
    comparativo = leer_json("comparativo_locales.json") or []

    fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    var_dia   = resumen.get("variacion_dia")
    var_mes   = resumen.get("variacion_mes")
    total     = resumen.get("total_productos", 0)
    locales_data = resumen.get("locales", {})

    # Tarjetas por local
    local_cards = ""
    for loc in LOCALES:
        ld = locales_data.get(loc, {})
        v = ld.get("variacion_dia")
        n = ld.get("total_productos", 0)
        emoji = LOCAL_EMOJIS.get(loc, "📍")
        local_cards += f"""
        <div class="stat-card">
          <div class="label">{emoji} {loc}</div>
          <div class="value" style="color:{color_pct(v)}">{fmt_pct(v)}</div>
          <div class="sub">{n} items hoy</div>
        </div>"""

    # Tabs de locales
    local_tabs_html = ""
    local_panels_html = ""
    for i, loc in enumerate(LOCALES):
        active = "active" if i == 0 else ""
        local_tabs_html += f'<button class="local-tab {active}" onclick="cambiarLocal(\'{loc}\', this)">{LOCAL_EMOJIS.get(loc,"")} {loc}</button>\n'

    # Panel global
    graficos_js  = json.dumps(graficos, ensure_ascii=False)
    rank_dia_js  = json.dumps(rank_dia[:25], ensure_ascii=False)
    rank_7d_js   = json.dumps(rank_7d[:25], ensure_ascii=False)
    rank_mes_js  = json.dumps(rank_mes[:25], ensure_ascii=False)
    rank_loc_js  = json.dumps(rank_local, ensure_ascii=False)
    comparativo_js = json.dumps(comparativo[:60], ensure_ascii=False)
    locales_data_js = json.dumps(locales_data, ensure_ascii=False)

    # Filas comparativo
    filas_comp = ""
    for row in comparativo[:40]:
        prod = row.get("producto", "")[:40]
        carta = row.get("carta", "")
        rubro = row.get("rubro", "")
        vals = []
        for loc in LOCALES:
            v = row.get(loc)
            if v:
                vals.append(f'<td style="font-family:\'IBM Plex Mono\',monospace;font-size:0.82rem">${v:,.0f}</td>')
            else:
                vals.append('<td style="color:var(--muted)">—</td>')
        # Highlight diferencias
        prices = [row.get(loc) for loc in LOCALES if row.get(loc)]
        if len(prices) > 1 and max(prices) > min(prices):
            diff = round((max(prices)/min(prices)-1)*100, 1)
            diff_str = f'<span style="color:#f59e0b;font-size:0.75rem">+{diff}%</span>'
        else:
            diff_str = '<span style="color:#64748b;font-size:0.75rem">igual</span>'

        filas_comp += f"""<tr>
          <td><div style="font-size:0.85rem">{prod}</div><div style="font-size:0.7rem;color:var(--muted)">{carta} · {rubro}</div></td>
          {"".join(vals)}
          <td>{diff_str}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Rock & Feller's Price Tracker</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;700&family=IBM+Plex+Sans:wght@400;600;700&display=swap');
  :root {{
    --bg: #0a0c12; --surface: #13161f; --surface2: #1a1d27; --border: #252836;
    --accent: #0ea5e9; --accent2: #6366f1;
    --red: #ef4444; --green: #22c55e; --amber: #f59e0b; --purple: #8b5cf6;
    --text: #e2e8f0; --muted: #64748b;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'IBM Plex Sans', sans-serif; }}

  header {{
    background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 1.25rem 2rem; display: flex; justify-content: space-between;
    align-items: center; flex-wrap: wrap; gap: 1rem;
  }}
  header h1 {{ font-family: 'IBM Plex Mono', monospace; font-size: 1.25rem; color: var(--accent); }}
  header .tagline {{ font-size: 0.78rem; color: var(--muted); margin-top: 0.2rem; }}

  .container {{ max-width: 1300px; margin: 0 auto; padding: 1.5rem 1rem 3rem; }}

  /* HERO STATS */
  .hero {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; margin-bottom: 1.5rem; }}
  .stat-card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 1.2rem; text-align: center;
  }}
  .stat-card .label {{ font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 0.4rem; }}
  .stat-card .value {{ font-family: 'IBM Plex Mono', monospace; font-size: 1.8rem; font-weight: 700; }}
  .stat-card .sub {{ font-size: 0.75rem; color: var(--muted); margin-top: 0.25rem; }}

  /* MAIN TABS (locales) */
  .main-nav {{
    display: flex; gap: 0; margin-bottom: 1.5rem;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; overflow: hidden; flex-wrap: wrap;
  }}
  .local-tab {{
    flex: 1; padding: 0.75rem 1.25rem; border: none; background: transparent;
    color: var(--muted); cursor: pointer; font-family: 'IBM Plex Mono', monospace;
    font-size: 0.82rem; transition: all 0.2s; border-right: 1px solid var(--border);
    min-width: 120px;
  }}
  .local-tab:last-child {{ border-right: none; }}
  .local-tab.active {{ background: var(--accent); color: #fff; }}
  .local-tab:hover:not(.active) {{ background: var(--surface2); color: var(--text); }}

  /* LOCAL PANELS */
  .local-panel {{ display: none; }}
  .local-panel.active {{ display: block; }}

  /* CARTA TABS */
  .carta-nav {{
    display: flex; gap: 0.4rem; margin-bottom: 1.25rem; flex-wrap: wrap;
  }}
  .carta-tab {{
    padding: 0.4rem 0.9rem; border-radius: 20px; border: 1px solid var(--border);
    background: transparent; color: var(--muted); cursor: pointer;
    font-size: 0.8rem; transition: all 0.2s;
  }}
  .carta-tab.active {{ border-color: var(--accent); color: var(--accent); background: rgba(14,165,233,0.08); }}
  .carta-tab:hover:not(.active) {{ border-color: var(--muted); color: var(--text); }}

  .carta-panel {{ display: none; }}
  .carta-panel.active {{ display: block; }}

  /* SECTION */
  .section {{ margin-bottom: 2rem; }}
  .section-title {{
    font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem;
    text-transform: uppercase; letter-spacing: 0.15em; color: var(--muted);
    margin-bottom: 0.85rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 0.5rem;
  }}

  /* CHARTS */
  .chart-wrap {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; padding: 1.25rem; height: 280px;
  }}
  .period-tabs {{ display: flex; gap: 0.4rem; margin-bottom: 1rem; }}
  .period-tab {{
    padding: 0.3rem 0.7rem; border-radius: 6px; border: 1px solid var(--border);
    background: transparent; color: var(--muted); cursor: pointer; font-size: 0.75rem;
    font-family: 'IBM Plex Mono', monospace;
  }}
  .period-tab.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}

  /* TABLES */
  .table-wrap {{ overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  th {{
    background: var(--surface); padding: 0.6rem 0.9rem; text-align: left;
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--muted); border-bottom: 1px solid var(--border); white-space: nowrap;
  }}
  td {{ padding: 0.55rem 0.9rem; border-bottom: 1px solid var(--border); }}
  tr:hover td {{ background: rgba(255,255,255,0.02); }}

  /* RUBROS TABLE */
  .rubros-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(260px,1fr));
    gap: 0.75rem; margin-top: 0.75rem;
  }}
  .rubro-card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 1rem;
  }}
  .rubro-card .rubro-name {{ font-size: 0.82rem; font-weight: 600; margin-bottom: 0.4rem; }}
  .rubro-card .rubro-pct {{ font-family: 'IBM Plex Mono', monospace; font-size: 1.1rem; font-weight: 700; }}

  /* GRID */
  .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; }}
  @media (max-width: 700px) {{
    .grid2 {{ grid-template-columns: 1fr; }}
    .main-nav {{ flex-direction: column; }}
  }}

  /* GLOBAL PANEL */
  #panel-global {{ margin-bottom: 2rem; }}

  /* BADGE */
  .badge-carta {{
    display: inline-block; padding: 0.15rem 0.45rem; border-radius: 4px;
    font-size: 0.68rem; font-family: 'IBM Plex Mono', monospace;
  }}

  footer {{
    text-align: center; padding: 2rem; color: var(--muted);
    font-size: 0.72rem; border-top: 1px solid var(--border);
    font-family: 'IBM Plex Mono', monospace;
  }}
</style>
</head>
<body>

<header>
  <div>
    <h1>🎸 ROCK & FELLER'S PRICE TRACKER</h1>
    <div class="tagline">Orono · Alto Rosario · Savoy — Restaurante · Cafetería · Vinos · Cocktails</div>
  </div>
  <div style="font-family:'IBM Plex Mono',monospace;font-size:0.78rem;color:var(--muted)">
    Actualizado: {fecha_str}
  </div>
</header>

<div class="container">

  <!-- HERO STATS -->
  <div class="hero" style="margin-top:1rem">
    <div class="stat-card">
      <div class="label">Variación Global Hoy</div>
      <div class="value" style="color:{color_pct(var_dia)}">{fmt_pct(var_dia)}</div>
      <div class="sub">{total} items · 3 locales</div>
    </div>
    <div class="stat-card">
      <div class="label">Variación 30 días</div>
      <div class="value" style="color:{color_pct(var_mes)}">{fmt_pct(var_mes)}</div>
    </div>
    {local_cards}
  </div>

  <!-- NAVEGACION PRINCIPAL: GLOBAL + LOCALES -->
  <div class="main-nav" style="margin-bottom:0">
    <button class="local-tab active" onclick="cambiarPanel('global', this)" style="background:var(--accent);color:#fff">🌐 Global</button>
    {local_tabs_html}
  </div>
  <div style="height:1.5rem"></div>

  <!-- PANEL GLOBAL -->
  <div id="panel-global" class="local-panel active">

    <div class="section">
      <div class="section-title">📈 Evolución de precios globales</div>
      <div class="period-tabs" id="period-global">
        <button class="period-tab active" onclick="cambiarPeriodoGlobal('7d',this)">7d</button>
        <button class="period-tab" onclick="cambiarPeriodoGlobal('30d',this)">30d</button>
        <button class="period-tab" onclick="cambiarPeriodoGlobal('6m',this)">6m</button>
      </div>
      <div class="chart-wrap"><canvas id="chartGlobal"></canvas></div>
    </div>

    <div class="section">
      <div class="section-title">📊 Comparativo entre locales</div>
      <div class="period-tabs" id="period-locales">
        <button class="period-tab active" onclick="cambiarPeriodoLocales('7d',this)">7d</button>
        <button class="period-tab" onclick="cambiarPeriodoLocales('30d',this)">30d</button>
        <button class="period-tab" onclick="cambiarPeriodoLocales('6m',this)">6m</button>
      </div>
      <div class="chart-wrap"><canvas id="chartLocales"></canvas></div>
    </div>

    <div class="section">
      <div class="section-title">📊 Comparativo por carta</div>
      <div class="chart-wrap"><canvas id="chartCartas"></canvas></div>
    </div>

    <div class="section">
      <div class="section-title">🔄 Precios entre locales — productos comunes</div>
      <div style="font-size:0.78rem;color:var(--muted);margin-bottom:0.75rem">Solo productos que aparecen en más de un local</div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Producto</th>
              <th>Orono</th>
              <th>Alto Rosario</th>
              <th>Savoy</th>
              <th>Dif. max</th>
            </tr>
          </thead>
          <tbody id="tabla-comp">
            {filas_comp}
          </tbody>
        </table>
      </div>
    </div>

    <div class="section">
      <div class="section-title">🏆 Rankings globales</div>
      <div class="period-tabs" id="rank-tabs-global">
        <button class="period-tab active" onclick="mostrarRankingGlobal('dia',this)">Hoy</button>
        <button class="period-tab" onclick="mostrarRankingGlobal('7d',this)">7 días</button>
        <button class="period-tab" onclick="mostrarRankingGlobal('mes',this)">30 días</button>
      </div>
      <div class="grid2" style="margin-top:1rem">
        <div>
          <div style="font-size:0.78rem;color:var(--muted);margin-bottom:0.6rem">🔥 Más subieron</div>
          <div class="table-wrap">
            <table><thead><tr><th>#</th><th>Producto</th><th>Local</th><th>Var %</th><th>Precio</th></tr></thead><tbody id="rank-sube-global"></tbody></table>
          </div>
        </div>
        <div>
          <div style="font-size:0.78rem;color:var(--muted);margin-bottom:0.6rem">📉 Más bajaron</div>
          <div class="table-wrap">
            <table><thead><tr><th>#</th><th>Producto</th><th>Local</th><th>Var %</th><th>Precio</th></tr></thead><tbody id="rank-baja-global"></tbody></table>
          </div>
        </div>
      </div>
    </div>

  </div>

  <!-- PANELES POR LOCAL -->
  {"".join([f'''
  <div id="panel-{loc.replace(' ','-')}" class="local-panel">

    <div class="section">
      <div class="section-title">{LOCAL_EMOJIS.get(loc,"")} {loc} — Evolución de precios</div>
      <div class="period-tabs">
        <button class="period-tab active" onclick="cambiarPeriodoLocal('{loc}','7d',this)">7d</button>
        <button class="period-tab" onclick="cambiarPeriodoLocal('{loc}','30d',this)">30d</button>
        <button class="period-tab" onclick="cambiarPeriodoLocal('{loc}','6m',this)">6m</button>
      </div>
      <div class="chart-wrap"><canvas id="chart-{loc.replace(' ','-')}"></canvas></div>
    </div>

    <div class="section">
      <div class="section-title">📋 Cartas de {loc}</div>
      <div class="carta-nav" id="carta-nav-{loc.replace(' ','-')}">
        CARTA_TABS_PLACEHOLDER_{loc.replace(' ','_')}
      </div>
      CARTA_PANELS_PLACEHOLDER_{loc.replace(' ','_')}
    </div>

    <div class="section">
      <div class="section-title">🏆 Rankings de {loc}</div>
      <div class="grid2">
        <div>
          <div style="font-size:0.78rem;color:var(--muted);margin-bottom:0.6rem">🔥 Más subieron hoy</div>
          <div class="table-wrap">
            <table><thead><tr><th>#</th><th>Producto</th><th>Carta</th><th>Var %</th><th>Precio</th></tr></thead><tbody id="rank-{loc.replace(' ','-')}-sube"></tbody></table>
          </div>
        </div>
        <div>
          <div style="font-size:0.78rem;color:var(--muted);margin-bottom:0.6rem">📉 Más bajaron hoy</div>
          <div class="table-wrap">
            <table><thead><tr><th>#</th><th>Producto</th><th>Carta</th><th>Var %</th><th>Precio</th></tr></thead><tbody id="rank-{loc.replace(' ','-')}-baja"></tbody></table>
          </div>
        </div>
      </div>
    </div>

  </div>
  ''' for loc in LOCALES])}

</div>

<footer>
  Datos de rockandfellers.com.ar via Livewire · Locales: Orono · Alto Rosario · Savoy<br>
  RFBOT · Actualización automática diaria via GitHub Actions
</footer>

<script>
const GRAFICOS = {graficos_js};
const RANK_DIA = {rank_dia_js};
const RANK_7D  = {rank_7d_js};
const RANK_MES = {rank_mes_js};
const RANK_LOCAL = {rank_loc_js};
const LOCALES_DATA = {locales_data_js};
const CARTAS_COLORS = {{"Restaurante":"#ef4444","Cafeteria":"#f59e0b","Vinos y Espumantes":"#8b5cf6","Cocktails":"#0ea5e9"}};

let charts = {{}};

// ── PANEL SWITCHING ─────────────────────────────────────────────────────────
function cambiarPanel(id, btn) {{
  document.querySelectorAll('.local-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.local-tab').forEach(t => {{
    t.classList.remove('active');
    t.style.background = '';
    t.style.color = '';
  }});
  document.getElementById('panel-' + id.replace(/ /g,'-')).classList.add('active');
  btn.classList.add('active');
  btn.style.background = 'var(--accent)';
  btn.style.color = '#fff';
  
  // Init charts for this panel
  if (id === 'global') {{
    renderChartGlobal('7d');
    renderChartLocales('7d');
    renderChartCartas('7d');
    mostrarRankingGlobal('dia', document.querySelector('#rank-tabs-global .period-tab'));
  }} else {{
    renderChartLocal(id, '7d');
    renderRankingLocal(id);
    renderRubros(id);
  }}
}}

function cambiarLocal(loc, btn) {{
  cambiarPanel(loc, btn);
}}

// ── CHARTS GLOBAL ────────────────────────────────────────────────────────────
function renderChartGlobal(periodo) {{
  const datos = GRAFICOS[periodo]?.total || [];
  if (charts.global) charts.global.destroy();
  const ctx = document.getElementById('chartGlobal').getContext('2d');
  charts.global = new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: datos.map(d => d.fecha),
      datasets: [{{ label: 'Total', data: datos.map(d => d.pct),
        borderColor: '#0ea5e9', backgroundColor: 'rgba(14,165,233,0.06)',
        borderWidth: 2, pointRadius: datos.length > 60 ? 0 : 2, tension: 0.3, fill: true }}]
    }},
    options: chartOpts()
  }});
}}

function cambiarPeriodoGlobal(p, btn) {{
  setActive('#period-global', btn);
  renderChartGlobal(p);
}}

// ── CHART LOCALES ─────────────────────────────────────────────────────────────
const LOCAL_COLORS = {{"Orono":"#0ea5e9","Alto Rosario":"#f59e0b","Savoy":"#22c55e"}};

function renderChartLocales(periodo) {{
  const por_local = GRAFICOS[periodo]?.por_local || {{}};
  if (charts.locales) charts.locales.destroy();
  const ctx = document.getElementById('chartLocales').getContext('2d');
  const datasets = Object.entries(por_local).map(([loc, datos]) => ({{
    label: loc,
    data: datos.map(d => ({{x: d.fecha, y: d.pct}})),
    borderColor: LOCAL_COLORS[loc] || '#888',
    backgroundColor: 'transparent',
    borderWidth: 2,
    pointRadius: datos.length > 60 ? 0 : 2,
    tension: 0.3
  }}));
  const allDates = Object.values(por_local).flat().map(d => d.fecha).filter((v,i,a) => a.indexOf(v)===i).sort();
  charts.locales = new Chart(ctx, {{
    type: 'line',
    data: {{ labels: allDates, datasets }},
    options: chartOpts(true)
  }});
}}

function cambiarPeriodoLocales(p, btn) {{
  setActive('#period-locales', btn);
  renderChartLocales(p);
}}

// ── CHART CARTAS ──────────────────────────────────────────────────────────────
function renderChartCartas(periodo) {{
  const por_carta = GRAFICOS[periodo]?.por_carta || {{}};
  if (charts.cartas) charts.cartas.destroy();
  const ctx = document.getElementById('chartCartas').getContext('2d');
  const datasets = Object.entries(por_carta).map(([carta, datos]) => ({{
    label: carta,
    data: datos.map(d => ({{x: d.fecha, y: d.pct}})),
    borderColor: CARTAS_COLORS[carta] || '#888',
    backgroundColor: 'transparent',
    borderWidth: 2,
    pointRadius: datos.length > 60 ? 0 : 2,
    tension: 0.3
  }}));
  const allDates = Object.values(por_carta).flat().map(d => d.fecha).filter((v,i,a) => a.indexOf(v)===i).sort();
  charts.cartas = new Chart(ctx, {{
    type: 'line',
    data: {{ labels: allDates, datasets }},
    options: chartOpts(true)
  }});
}}

// ── CHARTS POR LOCAL ──────────────────────────────────────────────────────────
function renderChartLocal(loc, periodo) {{
  const cid = 'chart-' + loc.replace(/ /g,'-');
  if (charts[cid]) charts[cid].destroy();
  const datos = GRAFICOS[periodo]?.por_local?.[loc] || [];
  const ctx = document.getElementById(cid)?.getContext('2d');
  if (!ctx) return;
  charts[cid] = new Chart(ctx, {{
    type: 'line',
    data: {{
      labels: datos.map(d => d.fecha),
      datasets: [{{ label: loc, data: datos.map(d => d.pct),
        borderColor: LOCAL_COLORS[loc] || '#0ea5e9',
        backgroundColor: 'rgba(14,165,233,0.06)',
        borderWidth: 2, pointRadius: datos.length > 60 ? 0 : 2, tension: 0.3, fill: true }}]
    }},
    options: chartOpts()
  }});
}}

function cambiarPeriodoLocal(loc, p, btn) {{
  const nav = btn.closest('.period-tabs');
  nav.querySelectorAll('.period-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  renderChartLocal(loc, p);
}}

// ── RUBROS POR CARTA ──────────────────────────────────────────────────────────
function renderRubros(loc) {{
  const locData = LOCALES_DATA[loc];
  if (!locData) return;
  for (const [cartaKey, cartaData] of Object.entries(locData.cartas || {{}})) {{
    const containerId = 'rubros-' + loc.replace(/ /g,'-') + '-' + cartaKey;
    const container = document.getElementById(containerId);
    if (!container) continue;
    const rubros = cartaData.rubros || [];
    if (!rubros.length) {{
      container.innerHTML = '<div style="color:var(--muted);font-size:0.82rem;padding:0.75rem">Sin datos de variación aún (se necesita al menos 2 días)</div>';
      continue;
    }}
    container.innerHTML = rubros.map(r => {{
      const c = r.variacion > 0 ? '#ef4444' : r.variacion < 0 ? '#22c55e' : '#888';
      const signo = r.variacion > 0 ? '+' : '';
      return `<div class="rubro-card">
        <div class="rubro-name">${{r.rubro}}</div>
        <div class="rubro-pct" style="color:${{c}}">${{signo}}${{r.variacion?.toFixed(2)}}%</div>
        <div style="font-size:0.72rem;color:var(--muted);margin-top:0.3rem">
          ⬆ ${{r.subieron}} · ⬇ ${{r.bajaron}} · Total: ${{r.total}}
        </div>
      </div>`;
    }}).join('');
  }}
}}

// ── CARTA SWITCHING ───────────────────────────────────────────────────────────
function cambiarCarta(loc, cartaKey, btn) {{
  const locId = loc.replace(/ /g,'-');
  document.querySelectorAll('#carta-nav-'+locId+' .carta-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('[id^="carta-'+locId+'"]').forEach(p => p.classList.remove('active'));
  document.getElementById('carta-'+locId+'-'+cartaKey)?.classList.add('active');
}}

// ── RANKINGS ─────────────────────────────────────────────────────────────────
function mostrarRankingGlobal(p, btn) {{
  setActive('#rank-tabs-global', btn);
  const data = p==='dia' ? RANK_DIA : p==='7d' ? RANK_7D : RANK_MES;
  const sube = data.filter(x => (x.diff_pct||0) > 0).slice(0,12);
  const baja = [...data].filter(x => (x.diff_pct||0) < 0).sort((a,b)=>a.diff_pct-b.diff_pct).slice(0,12);
  renderRankingTable('rank-sube-global', sube, false, true);
  renderRankingTable('rank-baja-global', baja, true, true);
}}

function renderRankingLocal(loc) {{
  const data = RANK_LOCAL[loc] || [];
  const sube = data.filter(x => (x.diff_pct||0) > 0).slice(0,10);
  const baja = [...data].filter(x => (x.diff_pct||0) < 0).sort((a,b)=>a.diff_pct-b.diff_pct).slice(0,10);
  const locId = loc.replace(/ /g,'-');
  renderRankingTableCarta('rank-'+locId+'-sube', sube, false);
  renderRankingTableCarta('rank-'+locId+'-baja', baja, true);
}}

function renderRankingTable(id, data, esBaja, showLocal) {{
  const tb = document.getElementById(id);
  if (!tb) return;
  if (!data.length) {{ tb.innerHTML = '<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:1rem">Sin datos aún</td></tr>'; return; }}
  tb.innerHTML = data.map((p,i) => {{
    const color = esBaja ? '#22c55e' : '#ef4444';
    const signo = p.diff_pct > 0 ? '+' : '';
    const cartaColor = CARTAS_COLORS[p.carta] || '#888';
    return `<tr>
      <td style="color:var(--muted);font-size:0.72rem">${{i+1}}</td>
      <td><div style="font-size:0.82rem">${{(p.nombre||'').substring(0,28)}}</div>
          <div style="font-size:0.68rem;color:var(--muted)">${{p.rubro||''}}</div></td>
      <td><span style="font-size:0.7rem;color:${{cartaColor}}">${{p.local||''}}</span></td>
      <td style="color:${{color}};font-weight:700;font-family:'IBM Plex Mono',monospace">${{signo}}${{p.diff_pct?.toFixed(1)}}%</td>
      <td style="font-family:'IBM Plex Mono',monospace;font-size:0.8rem">${{p.precio_hoy ? '$'+Number(p.precio_hoy).toLocaleString('es-AR') : '—'}}</td>
    </tr>`;
  }}).join('');
}}

function renderRankingTableCarta(id, data, esBaja) {{
  const tb = document.getElementById(id);
  if (!tb) return;
  if (!data.length) {{ tb.innerHTML = '<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:1rem">Sin datos aún</td></tr>'; return; }}
  tb.innerHTML = data.map((p,i) => {{
    const color = esBaja ? '#22c55e' : '#ef4444';
    const signo = p.diff_pct > 0 ? '+' : '';
    const cartaColor = CARTAS_COLORS[p.carta] || '#888';
    return `<tr>
      <td style="color:var(--muted);font-size:0.72rem">${{i+1}}</td>
      <td><div style="font-size:0.82rem">${{(p.nombre||'').substring(0,28)}}</div>
          <div style="font-size:0.68rem;color:var(--muted)">${{p.rubro||''}}</div></td>
      <td><span style="font-size:0.7rem;color:${{cartaColor}}">${{p.carta||''}}</span></td>
      <td style="color:${{color}};font-weight:700;font-family:'IBM Plex Mono',monospace">${{signo}}${{p.diff_pct?.toFixed(1)}}%</td>
      <td style="font-family:'IBM Plex Mono',monospace;font-size:0.8rem">${{p.precio_hoy ? '$'+Number(p.precio_hoy).toLocaleString('es-AR') : '—'}}</td>
    </tr>`;
  }}).join('');
}}

// ── UTILS ─────────────────────────────────────────────────────────────────────
function setActive(selector, btn) {{
  document.querySelectorAll(selector + ' .period-tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
}}

function chartOpts(legend=false) {{
  return {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: legend, labels: {{ color: '#94a3b8', font: {{ size: 11 }} }} }} }},
    scales: {{
      x: {{ ticks: {{ color: '#64748b', maxTicksLimit: 8 }}, grid: {{ color: '#1e2130' }} }},
      y: {{
        ticks: {{ color: '#64748b', callback: v => (v>0?'+':'')+v.toFixed(1)+'%' }},
        grid: {{ color: '#1e2130' }},
        afterDataLimits: axis => {{
          if (axis.min > 0) axis.min = 0;
          if (axis.max < 0) axis.max = 0;
        }}
      }}
    }}
  }};
}}

// ── INIT ─────────────────────────────────────────────────────────────────────
renderChartGlobal('7d');
renderChartLocales('7d');
renderChartCartas('7d');
mostrarRankingGlobal('dia', document.querySelector('#rank-tabs-global .period-tab'));
</script>
</body>
</html>"""

    ruta = DIR_DOCS / "index.html"
    html_final = html

    # Post-process: replace carta tab/panel placeholders per local
    for loc in LOCALES:
        loc_id = loc.replace(' ', '-')
        loc_key = loc.replace(' ', '_')

        # Carta tabs
        tabs_html = ""
        for j, (ck, cl) in enumerate(CARTAS.items()):
            active = "active" if j == 0 else ""
            emoji = CARTA_EMOJIS.get(ck, "")
            tabs_html += f'<button class="carta-tab {active}" onclick="cambiarCarta(\'{loc}\',\'{ck}\',this)">{emoji} {cl}</button>\n'
        html_final = html_final.replace(f"CARTA_TABS_PLACEHOLDER_{loc_key}", tabs_html)

        # Carta panels
        panels_html = ""
        for j, (ck, cl) in enumerate(CARTAS.items()):
            active = "active" if j == 0 else ""
            panels_html += f"""
      <div class="carta-panel {active}" id="carta-{loc_id}-{ck}">
        <div class="rubros-grid" id="rubros-{loc_id}-{ck}">
          <div style="color:var(--muted);font-size:0.82rem;padding:1rem">Cargando datos...</div>
        </div>
      </div>"""
        html_final = html_final.replace(f"CARTA_PANELS_PLACEHOLDER_{loc_key}", panels_html)

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(html_final)
    print(f"✅ Web RFBOT generada: {ruta}")
    print(f"   Locales: Orono, Alto Rosario, Savoy")
    print(f"   Cartas: Restaurante, Cafetería, Vinos y Espumantes, Cocktails")

if __name__ == "__main__":
    main()
