// Tests for app/frontend/client/metrics.js and the number formatting in common.js.
// Run with `uv run pytest` (tests/test_js.py) or directly: node --test tests/js

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// The site's scripts are plain browser files, so load them into one context like the page does.
const client = path.join(__dirname, "..", "..", "app", "frontend", "client");
const src = ["common.js", "metrics.js"].map((f) => fs.readFileSync(path.join(client, f), "utf8")).join("\n");
const m = vm.runInContext(
  `${src}\n({ fmtChange, fmtPct, lastFourPeriods, growth, lastYearOf, netDebt, ebitdaR12, netDebtToEbitda, equityRatio, quickRatio })`,
  vm.createContext({}),
);

const quarter = (period, values, extra = {}) => ({ period, values, ...extra });
const file = (quarters, currency = "SEK") => ({ currency, quarters });
const close = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-9, `${actual} != ${expected}`);

test("lastFourPeriods goes back across the year boundary", () => {
  assert.deepEqual([...m.lastFourPeriods("2026-Q2")], ["2026-Q2", "2026-Q1", "2025-Q4", "2025-Q3"]);
});

test("growth compares with the same quarter last year", () => {
  const fin = file([quarter("2025-Q2", { revenue: 100 }), quarter("2026-Q2", { revenue: 112 })]);
  close(m.growth(fin, fin.quarters[1], "revenue"), 0.12);
});

test("growth is null without a year-earlier quarter, a value or a base", () => {
  const fin = file([
    quarter("2025-Q1", { revenue: 0, ebit: null }),
    quarter("2026-Q1", { revenue: 50, ebit: 5 }),
    quarter("2026-Q2", { revenue: 60 }),
  ]);
  assert.equal(m.growth(fin, fin.quarters[1], "revenue"), null); // base 0
  assert.equal(m.growth(fin, fin.quarters[1], "ebit"), null); // base null
  assert.equal(m.growth(fin, fin.quarters[2], "revenue"), null); // no 2025-Q2
});

test("a smaller loss counts as an improvement", () => {
  const fin = file([quarter("2025-Q1", { ebit: -50 }), quarter("2026-Q1", { ebit: -20 })]);
  close(m.growth(fin, fin.quarters[1], "ebit"), 0.6);
});

test("growth is null across a currency change unless the report gives comparatives", () => {
  const fin = file(
    [
      quarter("2023-Q2", { revenue: 3800 }, { currency: "NOK" }),
      quarter("2024-Q2", { revenue: 333 }),
      quarter("2024-Q3", { revenue: 326 }, { comparatives: { revenue: 320 } }),
    ],
    "EUR",
  );
  fin.quarters.push(quarter("2023-Q3", { revenue: 3500 }, { currency: "NOK" }));
  assert.equal(m.lastYearOf(fin, fin.quarters[1]), null);
  assert.equal(m.growth(fin, fin.quarters[1], "revenue"), null);
  close(m.growth(fin, fin.quarters[2], "revenue"), 6 / 320);
});

test("comparatives are ignored when a same-currency quarter is stored", () => {
  const fin = file([
    quarter("2025-Q1", { revenue: 100 }),
    quarter("2026-Q1", { revenue: 110 }, { comparatives: { revenue: 50 } }),
  ]);
  close(m.growth(fin, fin.quarters[1], "revenue"), 0.1);
});

test("net debt needs both debts and cash", () => {
  assert.equal(m.netDebt({ short_term_debt: 10, long_term_debt: 90, cash: 30 }), 70);
  assert.equal(m.netDebt({ short_term_debt: 10, long_term_debt: null, cash: 30 }), null);
});

const r12Quarter = (period, ebit, extra) =>
  quarter(period, { ebit, depreciation: 5, short_term_debt: 20, long_term_debt: 80, cash: 10 }, extra);

test("R12 EBITDA needs 4 consecutive stored quarters in the same currency", () => {
  const fin = file(["2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2"].map((p) => r12Quarter(p, 10)));
  assert.equal(m.ebitdaR12(fin, fin.quarters[3]), 60);
  close(m.netDebtToEbitda(fin, fin.quarters[3]), 90 / 60);
  assert.equal(m.ebitdaR12(fin, fin.quarters[2]), null); // only 3 quarters

  const gap = file(["2025-Q2", "2025-Q4", "2026-Q1", "2026-Q2"].map((p) => r12Quarter(p, 10)));
  assert.equal(m.ebitdaR12(gap, gap.quarters[3]), null);

  const switched = file(["2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2"].map((p) => r12Quarter(p, 10)), "EUR");
  switched.quarters[0].currency = "NOK";
  assert.equal(m.ebitdaR12(switched, switched.quarters[3]), null);
});

test("net debt / EBITDA is null when R12 EBITDA is negative", () => {
  const fin = file(["2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2"].map((p) => r12Quarter(p, -20)));
  assert.equal(m.netDebtToEbitda(fin, fin.quarters[3]), null);
});

test("soliditet and kassalikviditet", () => {
  close(m.equityRatio({ total_equity: 450, total_assets: 1000 }), 0.45);
  close(m.quickRatio({ current_assets: 300, inventory: 80, current_liabilities: 200 }), 1.1);
  assert.equal(m.quickRatio({ current_assets: 300, inventory: null, current_liabilities: 200 }), null);
  assert.equal(m.equityRatio({ total_equity: 450, total_assets: 0 }), null);
});

const text = (html) => html.replace(/<[^>]+>/g, "").replace(/ /g, " ");

test("percentages have 2 decimals, and zero has no sign or colour", () => {
  assert.equal(text(m.fmtChange(12.345)), "+12,35 %");
  assert.match(m.fmtChange(12.345), /class="up"/);
  assert.equal(text(m.fmtChange(-3.2)), "−3,20 %");
  assert.match(m.fmtChange(-3.2), /class="down"/);
  assert.equal(text(m.fmtChange(0.004)), "0,00 %");
  assert.doesNotMatch(m.fmtChange(0.004), /class=/);
  assert.equal(m.fmtChange(-0.004), m.fmtChange(0));
  assert.equal(text(m.fmtPct(46.712, 2)), "46,71 %");
});

test("growth is shown in whole percent, and below ±0,5 % as a plain 0 %", () => {
  assert.equal(text(m.fmtChange(12.6, 0)), "+13 %");
  assert.equal(text(m.fmtChange(-7.14, 0)), "−7 %");
  assert.equal(text(m.fmtChange(0.4, 0)), "0 %");
  assert.doesNotMatch(m.fmtChange(-0.4, 0), /class=/);
});
