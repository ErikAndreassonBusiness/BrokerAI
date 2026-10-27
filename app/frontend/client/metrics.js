// Calculations for the financials table: stored figures in, a number or null out (null is shown as "–").
// No HTML here, so the logic is tested on its own in tests/js/metrics.test.js.
// `fin` is a data/financials/<ticker>.json file, `q` one of its quarters.

function parsePeriod(p) {
  const m = /^(\d{4})-Q([1-4])$/.exec(p || "");
  return m ? { y: +m[1], q: +m[2] } : null;
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

// Nothing is estimated: any missing input gives null.
const sum = (a, b) => (isNum(a) && isNum(b) ? a + b : null);
const ratio = (a, b) => (isNum(a) && isNum(b) && b !== 0 ? a / b : null);

// Relative change; the base is taken as an absolute value so a smaller loss counts as an improvement.
function change(cur, prev) {
  if (!isNum(cur) || !isNum(prev) || prev === 0) return null;
  return (cur - prev) / Math.abs(prev);
}

// A quarter can be reported in another currency than the file's (e.g. TOMRA in NOK before 2024).
const currencyOf = (fin, q) => q.currency || fin.currency;

// The stored quarter one year before q, if it is in the same currency (we never convert currencies).
function lastYearOf(fin, q) {
  const p = parsePeriod(q.period);
  const prev = p && fin.quarters.find((x) => x.period === `${p.y - 1}-Q${p.q}`);
  return prev && currencyOf(fin, prev) === currencyOf(fin, q) ? prev : null;
}

// Growth vs. the same quarter last year (0.12 = +12 %). Without a stored quarter in the same currency,
// the comparison figure printed in q's own report (q.comparatives, e.g. after TOMRA's switch to EUR) is used.
function growth(fin, q, key) {
  const prev = lastYearOf(fin, q);
  return change(q.values[key], prev ? prev.values[key] : q.comparatives?.[key]);
}

// Interest-bearing debt (incl. lease liabilities, see AGENT.md) minus cash.
function netDebt(v) {
  const debt = sum(v.short_term_debt, v.long_term_debt);
  return isNum(debt) && isNum(v.cash) ? debt - v.cash : null;
}

// EBITDA over the 4 quarters up to q; null unless all 4 are stored, complete and in q's currency.
function ebitdaR12(fin, q) {
  const last4 = lastFourPeriods(q.period).map((p) => fin.quarters.find((x) => x.period === p));
  if (last4.some((x) => !x || currencyOf(fin, x) !== currencyOf(fin, q))) return null;
  const ebitda = last4.map((x) => sum(x.values.ebit, x.values.depreciation));
  return ebitda.every(isNum) ? ebitda.reduce((a, b) => a + b, 0) : null;
}

function netDebtToEbitda(fin, q) {
  const ebitda = ebitdaR12(fin, q);
  // A negative EBITDA makes the multiple meaningless.
  return ebitda > 0 ? ratio(netDebt(q.values), ebitda) : null;
}

// Soliditet.
const equityRatio = (v) => ratio(v.total_equity, v.total_assets);

// Kassalikviditet.
const quickRatio = (v) => ratio(sum(v.current_assets, isNum(v.inventory) ? -v.inventory : null), v.current_liabilities);
