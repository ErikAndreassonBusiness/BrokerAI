// Tests for the revenue bar charts by geography and segment on the stock page (issue #49, ADR 0003).
// stock.js starts itself on load, so run it in a context with a fake page and a fake fetch.

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const client = path.join(__dirname, "..", "..", "app", "frontend", "client");
const src = ["common.js", "metrics.js", "stock.js"]
  .map((f) => fs.readFileSync(path.join(client, f), "utf8"))
  .join("\n");

const COMPANY = { ticker: "A.ST", name: "Alpha", currency: "SEK", report_currency: "SEK", ir_url: "https://example.com/ir" };
const GEO = "Revenue by geography";
const SEG = "Revenue by segment";
const NO_SEGMENT = "The company does not report revenue by segment";
const NO_GEOGRAPHY = "The company does not report revenue by geography";
const NO_BREAKDOWN = "No breakdown collected yet";

// Test values avoid the digit 0, so a stray "0" in a chart means a null was drawn as zero.
const quarter = (period, breakdown, extra = {}) => {
  const q = {
    period,
    report_date: "2026-07-17",
    source_url: `https://example.com/${period}.pdf`,
    values: { revenue: 1111 },
    ...extra,
  };
  if (breakdown !== undefined) q.breakdown = breakdown;
  return q;
};

async function openStockPage(quarters) {
  const app = { innerHTML: "Loading" };
  const files = {
    "data/companies.json": [COMPANY],
    "data/quotes.json": { quotes: {} },
    "data/updates.json": [],
    "data/financials/A.ST.json": { ticker: "A.ST", currency: "SEK", quarters },
  };
  const context = vm.createContext({
    document: { getElementById: () => app, title: "" },
    location: { search: "?t=A.ST" },
    URLSearchParams,
    encodeURIComponent,
    fetch: async (url) => {
      const body = files[String(url).split("?")[0]];
      if (body === undefined) return { ok: false, status: 404 };
      return { ok: true, status: 200, json: async () => body };
    },
  });
  vm.runInContext(src, context);
  for (let i = 0; i < 50 && app.innerHTML === "Loading"; i++) await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  return app.innerHTML;
}

// The part of the page belonging to one chart: from its title to the next chart title or heading.
function chartRegion(html, title) {
  const start = html.indexOf(title);
  if (start < 0) return "";
  const rest = html.slice(start + title.length);
  const ends = [rest.indexOf("<h2"), rest.indexOf(GEO), rest.indexOf(SEG)].filter((i) => i >= 0);
  return title + (ends.length ? rest.slice(0, Math.min(...ends)) : rest);
}
const text = (html) => html.replace(/<[^>]*>/g, " ");
const sv = (v) => v.toLocaleString("sv-SE", { maximumFractionDigits: 1 });
const hasZero = (html) => /(^|[^\d.,])0([^\d.,]|$)/.test(text(html)) || /(height|width)="0(\.0+)?"/.test(html);

const BOTH = [
  quarter("2026-Q1", { geography: { Sverige: 411, Norden: 222 }, segment: { Bil: 533, Lastbil: 111 } }),
  quarter("2026-Q2", { geography: { Sverige: 422, Norden: 233 }, segment: { Bil: 544, Lastbil: 122 } }),
  quarter("2026-Q3", { geography: { Sverige: 433, Norden: 244 }, segment: { Bil: 555, Lastbil: 133 } }),
];

test("REQ-49-1: one chart by geography and one by segment are drawn", async () => {
  const html = await openStockPage(BOTH);
  assert.equal(html.split(GEO).length - 1, 1);
  assert.equal(html.split(SEG).length - 1, 1);
  assert.ok(!html.includes(NO_BREAKDOWN));
  assert.ok(!html.includes(NO_SEGMENT));
  assert.ok(chartRegion(html, GEO).includes("<svg") || /class="[^"]*(bar|chart)/.test(chartRegion(html, GEO)));
});

test("REQ-49-2: quarters run oldest to newest and every part is in the legend and has values", async () => {
  const html = await openStockPage(BOTH);
  for (const [title, parts] of [[GEO, ["Sverige", "Norden"]], [SEG, ["Bil", "Lastbil"]]]) {
    const region = chartRegion(html, title);
    const at = ["2026-Q1", "2026-Q2", "2026-Q3"].map((p) => region.indexOf(p));
    assert.ok(at.every((i) => i >= 0), `${title}: every quarter is labelled`);
    assert.ok(at[0] < at[1] && at[1] < at[2], `${title}: oldest first`);
    for (const part of parts) assert.ok(region.includes(part), `${title}: legend has ${part}`);
  }
  const geo = text(chartRegion(html, GEO));
  for (const v of [411, 222, 422, 233, 433, 244]) assert.ok(geo.includes(String(v)), `value ${v}`);
});

test("REQ-49-3: a null part shows a dash and no zero is drawn or written", async () => {
  const quarters = [
    quarter("2026-Q1", { geography: { Sverige: 411, Övrigt: 222 }, segment: null }),
    quarter("2026-Q2", { geography: { Sverige: 422, Övrigt: null }, segment: null }),
  ];
  const region = chartRegion(await openStockPage(quarters), GEO);
  assert.ok(text(region).includes("–"));
  assert.ok(!hasZero(region), "no 0 drawn or written");
});

test("REQ-49-3: a quarter without breakdown after data is an empty slot, with no zero; older ones are dropped", async () => {
  const quarters = [
    quarter("2026-Q1"),
    quarter("2026-Q2", { geography: { Sverige: 422, Norden: 233 }, segment: { Bil: 544 } }),
    quarter("2026-Q3"),
    quarter("2026-Q4", { geography: { Sverige: 433, Norden: 244 }, segment: { Bil: 555 } }),
  ];
  const region = chartRegion(await openStockPage(quarters), GEO);
  assert.ok(!region.includes("2026-Q1"), "quarters before the first breakdown are dropped");
  assert.ok(region.includes("2026-Q3"), "the empty quarter keeps its slot");
  assert.ok(text(region).includes("–"));
  assert.ok(!hasZero(region));
  assert.ok(region.indexOf("2026-Q2") < region.indexOf("2026-Q3") && region.indexOf("2026-Q3") < region.indexOf("2026-Q4"));
});

test("REQ-49-3: a real value of 0 is written as 0, not as a gap", async () => {
  const q = [quarter("2026-Q1", { geography: { Sverige: 411, Norden: 0 }, segment: null })];
  assert.ok(hasZero(chartRegion(await openStockPage(q), GEO)));
});

test("a negative part is left out of the stack but listed with its value", async () => {
  const q = [quarter("2026-Q1", { geography: { Sverige: 411, Elim: -1234.5 }, segment: null })];
  const region = chartRegion(await openStockPage(q), GEO);
  assert.ok(text(region).includes("Elim"));
  assert.ok(region.includes("\u2212" + sv(1234.5)), "listed with a minus sign");
  assert.ok(!/flex-grow:-/.test(region));
});

test("bar height is proportional to the quarter total", async () => {
  const q = [
    quarter("2026-Q1", { geography: { Sverige: 100, Norden: 100 }, segment: null }),
    quarter("2026-Q2", { geography: { Sverige: 200, Norden: 200 }, segment: null }),
  ];
  const heights = [...chartRegion(await openStockPage(q), GEO).matchAll(/rev-stack"[^>]*height:([\d.]+)%/g)].map((m) => +m[1]);
  assert.deepEqual(heights, [50, 100]);
});

test("REQ-49-4: a part that exists only from a later quarter is its own series", async () => {
  const quarters = [
    quarter("2026-Q1", { geography: { Sverige: 411 }, segment: null }),
    quarter("2026-Q2", { geography: { Sverige: 422, Asien: 233 }, segment: null }),
  ];
  const region = chartRegion(await openStockPage(quarters), GEO);
  assert.ok(region.includes("Asien") && region.includes("Sverige"));
  assert.ok(text(region).includes("–"), "gap in the quarter where Asien is absent");
  assert.ok(!hasZero(region));
});

test("REQ-49-5: a dimension that is null in every quarter shows a note and no chart", async () => {
  const quarters = [
    quarter("2026-Q1", { geography: { Sverige: 411 }, segment: null }),
    quarter("2026-Q2", { geography: { Sverige: 422 }, segment: null }),
  ];
  const html = await openStockPage(quarters);
  assert.ok(html.includes(NO_SEGMENT));
  assert.ok(!chartRegion(html, SEG).includes("<svg"));
  assert.ok(html.includes(GEO));
  const geoNull = await openStockPage([quarter("2026-Q1", { geography: null, segment: { Bil: 511 } })]);
  assert.ok(geoNull.includes(NO_GEOGRAPHY));
});

test("REQ-49-6: a dimension missing in every quarter shows 'No breakdown collected yet' and no chart", async () => {
  const html = await openStockPage([quarter("2026-Q1"), quarter("2026-Q2", { segment: { Bil: 511 } })]);
  assert.ok(html.includes(NO_BREAKDOWN));
  assert.ok(!html.includes(NO_SEGMENT));
  assert.ok(!chartRegion(html, GEO).includes("<svg"));
  const none = await openStockPage([quarter("2026-Q1"), quarter("2026-Q2")]);
  assert.equal(none.split(NO_BREAKDOWN).length - 1, 2, "one note per dimension");
  assert.ok(!none.includes("<svg"));
});

test("REQ-49-7: amounts are in sv-SE format with the unit MSEK", async () => {
  const quarters = [quarter("2026-Q1", { geography: { Sverige: 1234.5, Norden: 222 }, segment: null })];
  const region = text(chartRegion(await openStockPage(quarters), GEO));
  assert.ok(region.includes(sv(1234.5)), sv(1234.5));
  assert.ok(sv(1234.5).includes(","), "decimal comma");
  assert.ok(region.includes("MSEK"));
});

test("REQ-49-7: each quarter shows its own unit and values are not converted", async () => {
  const quarters = [
    quarter("2026-Q1", { geography: { Sverige: 411 }, segment: null }, { currency: "EUR" }),
    quarter("2026-Q2", { geography: { Sverige: 422 }, segment: null }),
  ];
  const region = text(chartRegion(await openStockPage(quarters), GEO));
  assert.ok(region.includes("MEUR"));
  assert.ok(region.includes("MSEK"));
  assert.ok(region.includes("411") && region.includes("422"));
});

test("REQ-49-8: part names are plain text, not HTML", async () => {
  const quarters = [quarter("2026-Q1", { geography: { "<b>x</b>": 411 }, segment: { "<i>y</i>": 222 } })];
  const html = await openStockPage(quarters);
  assert.ok(html.includes("&lt;b&gt;x&lt;/b&gt;"));
  assert.ok(html.includes("&lt;i&gt;y&lt;/i&gt;"));
  assert.ok(!html.includes("<b>x</b>"));
  assert.ok(!html.includes("<i>y</i>"));
});

test("REQ-49-9: charts are inline SVG or CSS, with no new script or library", async () => {
  const html = await openStockPage(BOTH);
  const charts = chartRegion(html, GEO) + chartRegion(html, SEG);
  assert.ok(charts.length > GEO.length + SEG.length, "the charts exist");
  assert.ok(!/<script|<img|<canvas|<iframe/i.test(charts));
  const page = fs.readFileSync(path.join(client, "..", "templates", "stock.html"), "utf8");
  assert.ok(!/<script[^>]+src="https?:/i.test(page));
});
