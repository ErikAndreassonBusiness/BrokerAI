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

  document.title = company.name + " – BrokerAI";
  const irUrl = safeUrl(company.ir_url);
  app.innerHTML = `
    <a class="back" href="./">← All stocks</a>
    <h1>${esc(company.name)} <span class="muted">${esc(company.ticker)}</span></h1>
    ${irUrl ? `<a href="${esc(irUrl)}" rel="noopener">Investor relations</a>` : ""}
    ${renderKeyData(quotesFile.quotes[ticker] || {}, company)}
    <h2>Quarterly financials</h2>
    ${renderFinancials(financials)}
    ${renderNews(updates, ticker)}`;
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
  // A quarter can be reported in another currency than the file's (e.g. TOMRA in NOK before 2024).
  const currencyOf = (q) => q.currency || fin.currency;
  // y/y only makes sense in the same currency.
  const lastYearOf = (q) => {
    const prev = sameQuarterLastYear(quarters, q);
    return prev && currencyOf(prev) === currencyOf(q) ? prev : null;
  };
  const latest = quarters[quarters.length - 1];
  const lastYear = lastYearOf(latest);

  // EBITDA over the 4 quarters up to q; null unless all 4 are stored, complete and in q's currency.
  const ebitdaR12 = (q) => {
    const last4 = lastFourPeriods(q.period).map((p) => quarters.find((x) => x.period === p));
    if (last4.some((x) => !x || currencyOf(x) !== currencyOf(q))) return null;
    const ebitda = last4.map((x) => sum(x.values.ebit, x.values.depreciation));
    return ebitda.every(isNum) ? ebitda.reduce((a, b) => a + b, 0) : null;
  };
  const RATIOS = [
    ["Net debt", (q) => fmtNum(netDebt(q.values), 1)],
    [
      "Net debt / EBITDA (R12)",
      (q) => {
        const ebitda = ebitdaR12(q);
        // A negative EBITDA makes the multiple meaningless.
        const v = ebitda > 0 ? ratio(netDebt(q.values), ebitda) : null;
        return isNum(v) ? fmtNum(v, 1, 1) + "x" : "–";
      },
    ],
    ["Equity ratio (soliditet)", (q) => fmtShare(q.values.total_equity, q.values.total_assets)],
    [
      "Quick ratio (kassalikviditet)",
      (q) => {
        const v = q.values;
        const quick = isNum(v.current_assets) && isNum(v.inventory) ? v.current_assets - v.inventory : null;
        return fmtShare(quick, v.current_liabilities);
      },
    ],
  ];

  const head = quarters
    .map((q) => {
      const url = safeUrl(q.source_url);
      const other = currencyOf(q) !== fin.currency;
      const label = esc(q.period) + (other ? ` · ${esc(currencyOf(q))}` : "");
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
        return `<tr><td>${label}</td>${cells}<td class="yoy">${fmtYoy(latest, lastYear, key)}</td></tr>`;
      })
      .join("");
    const groupRow = (title) =>
      `<tr class="group"><td colspan="${quarters.length + 2}">${title}</td></tr>`;
    const growth = group.growth
      ? groupRow("Growth y/y (vs. same quarter last year)") +
        group.items
          .map(([key, label]) => {
            const cells = quarters
              .map((q) => `<td>${fmtYoy(q, lastYearOf(q), key)}</td>`)
              .join("");
            return `<tr><td>${label}</td>${cells}<td class="yoy"></td></tr>`;
          })
          .join("")
      : "";
    const ratios = group.ratios
      ? groupRow("Key ratios") +
        RATIOS.map(([label, fmt]) => {
          const cells = quarters.map((q) => `<td>${fmt(q)}</td>`).join("");
          return `<tr><td>${label}</td>${cells}<td class="yoy"></td></tr>`;
        }).join("")
      : "";
    return groupRow(group.title) + rows + growth + ratios;
  }).join("");

  return `
    <p class="muted">Millions of ${esc(fin.currency)} (EPS in ${esc(fin.currency)} per share)${
      quarters.some((q) => currencyOf(q) !== fin.currency)
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

// The ratios below give null ("–") when an input is missing; nothing is estimated.
const sum = (a, b) => (isNum(a) && isNum(b) ? a + b : null);
const ratio = (a, b) => (isNum(a) && isNum(b) && b !== 0 ? a / b : null);
// Debt includes lease liabilities (see AGENT.md).
const netDebt = (v) => {
  const debt = sum(v.short_term_debt, v.long_term_debt);
  return isNum(debt) && isNum(v.cash) ? debt - v.cash : null;
};

// a / b in whole percent.
function fmtShare(a, b) {
  const v = ratio(a, b);
  return isNum(v) ? fmtPct(v * 100, 0) : "–";
}

// "2026-Q2" -> ["2026-Q2", "2026-Q1", "2025-Q4", "2025-Q3"].
function lastFourPeriods(period) {
  let { y, q } = parsePeriod(period);
  const periods = [];
  for (let i = 0; i < 4; i++) {
    periods.push(`${y}-Q${q}`);
    [y, q] = q === 1 ? [y - 1, 4] : [y, q - 1];
  }
  return periods;
}

// A quarter vs. the same quarter last year, in %, green or red.
function fmtYoy(quarter, lastYear, key) {
  const v = lastYear ? change(quarter.values[key], lastYear.values[key]) : null;
  return v === null ? "–" : fmtChange(v * 100, 0);
}

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

init();
