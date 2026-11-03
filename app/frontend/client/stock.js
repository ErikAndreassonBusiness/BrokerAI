// Stock page: key data, the quarterly financials table and the stock's news.

const GROUPS = [
  {
    title: "Income statement",
    growth: true, // followed by a y/y growth row per line item
    items: [
      ["revenue", "Revenue"],
      ["gross_profit", "Gross profit"],
      ["ebit", "Operating income (EBIT)"],
      ["net_income", "Net income"],
      ["eps", "EPS (diluted)"],
    ],
  },
  {
    title: "Balance sheet",
    ratios: true, // followed by the key ratios
    items: [
      ["cash", "Cash"],
      ["inventory", "Inventory"],
      ["current_assets", "Current assets"],
      ["total_assets", "Total assets"],
      ["short_term_debt", "Short-term debt"],
      ["long_term_debt", "Long-term debt"],
      ["current_liabilities", "Current liabilities"],
      ["total_equity", "Total equity"],
    ],
  },
  {
    title: "Cash flow",
    items: [
      ["depreciation", "Depreciation & amortisation"],
      ["operating_cash_flow", "Operating cash flow"],
      ["capex", "Capex"],
      ["free_cash_flow", "Free cash flow"],
    ],
  },
];

async function init() {
  const app = document.getElementById("app");
  const ticker = new URLSearchParams(location.search).get("t");
  let companies, quotesFile, updates, financials;
  try {
    [companies, quotesFile, updates] = await Promise.all([
      loadJSON("data/companies.json"),
      loadJSON("data/quotes.json", { quotes: {} }),
      loadJSON("data/updates.json", []),
    ]);
  } catch (e) {
    showError(app, e);
    return;
  }

  const company = companies.find((c) => c.ticker === ticker);
  if (!company) {
    app.innerHTML = `<p class="card">Unknown stock. <a href="./">Back to the overview</a></p>`;
    return;
  }
  try {
    financials = await loadJSON(
      "data/financials/" + encodeURIComponent(ticker) + ".json",
      { quarters: [], currency: company.report_currency },
    );
  } catch (e) {
    showError(app, e);
    return;
  }

  const summary = await loadSummary(ticker);
  const letters = await loadLetters(ticker);

  document.title = company.name + " – BrokerAI";
  const irUrl = safeUrl(company.ir_url);
  app.innerHTML = `
    <a class="back" href="./">← All stocks</a>
    <h1>${esc(company.name)} <span class="muted">${esc(company.ticker)}</span></h1>
    ${irUrl ? `<a href="${esc(irUrl)}" rel="noopener">Investor relations</a>` : ""}
    ${renderKeyData(quotesFile.quotes[ticker] || {}, company)}
    <h2>Quarterly financials</h2>
    ${renderFinancials(financials)}
    ${renderNews(updates, ticker)}
    ${renderSummary(summary)}
    ${renderLetters(letters)}`;
}

// A missing or invalid summary file is not an error: the section just says there is none yet.
async function loadSummary(ticker) {
  try {
    const s = await loadJSON("data/summaries/" + encodeURIComponent(ticker) + ".json", null);
    return s && typeof s.summary === "string" && s.swot ? s : null;
  } catch (e) {
    return null;
  }
}

function renderKeyData(q, company) {
  const cur = esc(q.currency || company.currency);
  const cells = [
    ["Price", `${fmtNum(q.price, 2, 2)} ${cur}`],
    ["Today", fmtChange(q.change_pct)],
    ["Market cap", `${fmtNum(q.market_cap, 0)} M${cur}`],
    ["P/E", fmtNum(q.pe, 1, 1)],
    ["Dividend yield", fmtPct(q.dividend_yield, 2)],
    ["52-week low–high", `${fmtNum(q.low_52w, 2)} – ${fmtNum(q.high_52w, 2)}`],
    ["Quote time", fmtTime(q.quote_time)],
  ];
  return `<div class="keydata">${cells
    .map(
      ([label, value]) =>
        `<div class="card"><div class="label">${label}</div><div class="value">${value}</div></div>`,
    )
    .join("")}</div>`;
}

function renderFinancials(fin) {
  const quarters = fin.quarters;
  if (!quarters.length) {
    return `<p class="card empty muted">No quarterly figures yet. The report agent adds them.</p>`;
  }
  const latest = quarters[quarters.length - 1];
  const lastYear = lastYearOf(fin, latest);

  const head = quarters
    .map((q) => {
      const url = safeUrl(q.source_url);
      const other = currencyOf(fin, q) !== fin.currency;
      const label = esc(q.period) + (other ? ` · ${esc(currencyOf(fin, q))}` : "");
      const title = `Report published ${fmtDate(q.report_date)}`;
      return `<th title="${title}">${url ? `<a href="${esc(url)}" rel="noopener">${label}</a>` : label}</th>`;
    })
    .join("");
  const yoyHead = `<th class="yoy" title="${esc(latest.period)} vs. ${lastYear ? esc(lastYear.period) : "same quarter last year"}">y/y</th>`;

  const body = GROUPS.map((group) => {
    const rows = group.items
      .map(([key, label]) => {
        const digits = key === "eps" ? 2 : 1;
        const cells = quarters
          .map((q) => `<td>${fmtNum(q.values[key], digits, key === "eps" ? 2 : 0)}</td>`)
          .join("");
        return `<tr><td>${label}</td>${cells}<td class="yoy">${fmtGrowth(fin, latest, key)}</td></tr>`;
      })
      .join("");
    const groupRow = (title) =>
      `<tr class="group"><td colspan="${quarters.length + 2}">${title}</td></tr>`;
    // A calculated row: one cell per quarter, nothing in the y/y column.
    const metricRow = (label, cell) =>
      `<tr><td>${label}</td>${quarters.map((q) => `<td>${cell(q)}</td>`).join("")}<td class="yoy"></td></tr>`;
    const growth = group.growth
      ? groupRow("Growth y/y (vs. same quarter last year)") +
        group.items.map(([key, label]) => metricRow(label, (q) => fmtGrowth(fin, q, key))).join("")
      : "";
    const ratios = group.ratios
      ? groupRow("Key ratios") +
        RATIOS.map(([label, cell]) => metricRow(label, (q) => cell(fin, q))).join("")
      : "";
    return groupRow(group.title) + rows + growth + ratios;
  }).join("");

  return `
    <p class="muted">Millions of ${esc(fin.currency)} (EPS in ${esc(fin.currency)} per share)${
      quarters.some((q) => currencyOf(fin, q) !== fin.currency)
        ? ", unless another currency is shown next to the quarter"
        : ""
    }. Click a quarter to open its report.</p>
    <div class="table-wrap">
      <table class="financials">
        <thead><tr><th>Line item</th>${head}${yoyHead}</tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>`;
}

// The calculations are in metrics.js; these only format them.
const fmtShare = (v) => (isNum(v) ? fmtPct(v * 100, 2) : "–");
const fmtMultiple = (v) => (isNum(v) ? fmtNum(v, 1, 1) + "x" : "–");
const fmtGrowth = (fin, q, key) => {
  const v = growth(fin, q, key);
  return isNum(v) ? fmtChange(v * 100, 0) : "–"; // whole percent: the reports are rounded too
};

const RATIOS = [
  ["Net debt", (fin, q) => fmtNum(netDebt(q.values), 1)],
  ["Net debt / EBITDA (R12)", (fin, q) => fmtMultiple(netDebtToEbitda(fin, q))],
  ["Equity ratio (soliditet)", (fin, q) => fmtShare(equityRatio(q.values))],
  ["Quick ratio (kassalikviditet)", (fin, q) => fmtShare(quickRatio(q.values))],
];

function renderNews(updates, ticker) {
  const items = updates.flatMap((u) =>
    u.items.filter((i) => i.ticker === ticker).map((i) => ({ ...i, date: u.date })),
  );
  if (!items.length) return "";
  const list = items
    .map((item) => {
      return `<li><span class="muted">${fmtDate(item.date)}:</span> ${esc(item.text)}${sourceLink(item.url)}</li>`;
    })
    .join("");
  return `<h2>News</h2><div class="card"><ul>${list}</ul></div>`;
}

const SWOT_GROUPS = [
  ["strengths", "Strengths"],
  ["weaknesses", "Weaknesses"],
  ["opportunities", "Opportunities"],
  ["threats", "Threats"],
];

function renderSwotItem(item) {
  const links = (Array.isArray(item.sources) ? item.sources : [])
    .map((u, i) => {
      const url = safeUrl(u);
      return url ? ` <a href="${esc(url)}" target="_blank" rel="noopener" aria-label="Source ${i + 1}">[${i + 1}]</a>` : "";
    })
    .join("");
  return `<li>${esc(item.text)}${links}</li>`;
}

function renderSummary(data) {
  const head = `<h2>AI summary and SWOT</h2>`;
  if (!data) {
    return `<section class="ai-summary">${head}<p class="card empty muted">No summary yet. The report agent adds one.</p></section>`;
  }
  const groups = SWOT_GROUPS.map(([key, title]) => {
    const items = Array.isArray(data.swot[key]) ? data.swot[key] : [];
    const body = items.length ? `<ul>${items.map(renderSwotItem).join("")}</ul>` : `<p aria-label="None">–</p>`;
    return `<div class="card"><div class="label">${title}</div>${body}</div>`;
  }).join("");
  return `<section class="ai-summary">${head}
    <p class="muted">AI-generated, last updated ${fmtDate(data.updated)}.</p>
    <div class="card"><p>${esc(data.summary)}</p></div>
    <div class="swot">${groups}</div>
  </section>`;
}

// CEO letter comparison (AI-generated). A missing or invalid file just hides the section.
async function loadLetters(ticker) {
  try {
    const d = await loadJSON("data/ceo_letters/" + encodeURIComponent(ticker) + ".json", null);
    if (!d || !Array.isArray(d.comparisons)) return null;
    const isObj = (x) => x && typeof x === "object";
    const strings = (a) => (Array.isArray(a) ? a.filter((x) => typeof x === "string") : []);
    const comparisons = d.comparisons
      .filter((c) => isObj(c) && isObj(c.tone) && typeof c.period === "string")
      .map((c) => ({
        ...c,
        dropped_topics: strings(c.dropped_topics),
        new_topics: strings(c.new_topics),
        changed_wording: (Array.isArray(c.changed_wording) ? c.changed_wording : []).filter(isObj),
      }))
      .sort((a, b) => (a.period < b.period ? -1 : 1));
    return comparisons.length ? { ...d, comparisons } : null;
  } catch (e) {
    return null;
  }
}

function letterList(items) {
  return items.length ? `<ul>${items.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>` : `<p aria-label="None">–</p>`;
}

function renderComparison(c) {
  const url = safeUrl(c.source_url);
  const link = url ? ` <a href="${esc(url)}" target="_blank" rel="noopener">Report</a>` : "";
  const dropped = c.dropped_topics;
  const added = c.new_topics;
  const wording = c.changed_wording.map((w) => `${w.topic ?? "–"}: ${w.before ?? "–"} → ${w.after ?? "–"}`);
  return `<div class="card">
    <div class="label">${esc(c.period)} vs ${esc(c.compared_to)}${link}</div>
    <p>Tone: ${esc(c.tone.previous)} → ${esc(c.tone.current)}</p>
    <div class="label">Dropped topics</div>${letterList(dropped)}
    <div class="label">New topics</div>${letterList(added)}
    <div class="label">Changed wording</div>${letterList(wording)}
    <p>${esc(c.summary)}</p>
  </div>`;
}

function renderLetterTrend(data) {
  const t = data.trend;
  if (!t || typeof t.summary !== "string") return "";
  const cells = data.comparisons
    .filter((c) => c.period >= t.from && c.period <= t.to)
    .sort((a, b) => (a.period < b.period ? -1 : 1))
    .map((c) => `<span class="tone"><span class="muted">${esc(c.period)}</span> ${esc(c.tone.current)}</span>`)
    .join("");
  return `<div class="card"><div class="label">Trend ${esc(t.from)} → ${esc(t.to)}</div>
    <p>${esc(t.summary)}</p><div class="tone-row">${cells}</div></div>`;
}

// Never lets a bad letter file break the page.
function renderLetters(data) {
  try {
    return data ? renderLettersSection(data) : "";
  } catch (e) {
    return "";
  }
}

function renderLettersSection(data) {
  const [latest, ...older] = [...data.comparisons].reverse(); // loadLetters sorts oldest first
  const olderHtml = older
    .map((c) => `<details><summary>${esc(c.period)} vs ${esc(c.compared_to)}</summary>${renderComparison(c)}</details>`)
    .join("");
  return `<section class="ai-summary ceo-letters">
    <h2>CEO letter comparison</h2>
    <p class="muted">AI-generated</p>
    ${renderLetterTrend(data)}
    ${renderComparison(latest)}
    ${olderHtml}
  </section>`;
}

init();
