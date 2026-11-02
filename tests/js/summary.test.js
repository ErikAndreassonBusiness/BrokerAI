// Tests for the AI summary + SWOT section on the stock page (issue #43, ADR 0001).
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
const item = (text, sources = ["https://example.com/report"]) => ({ text, sources });
const SUMMARY = {
  ticker: "A.ST",
  updated: "2026-11-02",
  summary: "Alpha reported steady sales. Margins were stable.",
  swot: {
    strengths: [item("Strong order book.", ["https://example.com/one", "https://example.com/two"])],
    weaknesses: [item("High debt.")],
    opportunities: [item("New market.")],
    threats: [item("Price pressure.")],
  },
};

// files: path -> JSON value, or a string (invalid JSON), or undefined/missing (404).
async function openStockPage(summary) {
  const fetched = [];
  const files = {
    "data/companies.json": [COMPANY],
    "data/quotes.json": { quotes: {} },
    "data/updates.json": [],
    "data/financials/A.ST.json": { ticker: "A.ST", currency: "SEK", quarters: [] },
  };
  if (summary !== undefined) files["data/summaries/A.ST.json"] = summary;
  const app = { innerHTML: "Loading" };
  const context = vm.createContext({
    document: { getElementById: () => app, title: "" },
    location: { search: "?t=A.ST" },
    URLSearchParams,
    encodeURIComponent,
    fetch: async (url) => {
      const file = String(url).split("?")[0];
      fetched.push(file);
      const body = files[file];
      if (body === undefined) return { ok: false, status: 404 };
      return {
        ok: true,
        status: 200,
        json: async () => {
          if (typeof body === "string") throw new SyntaxError("Unexpected token");
          return body;
        },
      };
    },
  });
  vm.runInContext(src, context);
  for (let i = 0; i < 50 && app.innerHTML === "Loading"; i++) await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  return { html: app.innerHTML, fetched };
}

test("REQ-43-1: summary and the four SWOT groups with their items are shown", async () => {
  const { html, fetched } = await openStockPage(SUMMARY);
  assert.ok(fetched.includes("data/summaries/A.ST.json"));
  assert.ok(html.includes("Alpha reported steady sales. Margins were stable."));
  for (const group of ["Strengths", "Weaknesses", "Opportunities", "Threats"]) {
    assert.match(html, new RegExp(group, "i"));
  }
  for (const text of ["Strong order book.", "High debt.", "New market.", "Price pressure."]) {
    assert.ok(html.includes(text), text);
  }
});

test("REQ-43-2: the section is labelled AI-generated and shows the updated date", async () => {
  const { html } = await openStockPage(SUMMARY);
  assert.ok(html.includes("AI-generated"));
  assert.ok(html.includes("2026"), "the formatted date (fmtDate) should show the year");
  assert.ok(html.includes(new Date("2026-11-02T12:00:00").toLocaleDateString("sv-SE", { day: "numeric", month: "short", year: "numeric" })));
});

test("REQ-43-3: each item links to all its sources in a new tab", async () => {
  const { html } = await openStockPage(SUMMARY);
  for (const url of ["https://example.com/one", "https://example.com/two"]) {
    const tag = html.match(new RegExp(`<a [^>]*href="${url}"[^>]*>`));
    assert.ok(tag, url);
    assert.match(tag[0], /target="_blank"/);
    assert.match(tag[0], /rel="[^"]*noopener/);
  }
});

test("REQ-43-4: the AI section has its own heading and no notes are read from data/", async () => {
  const { html, fetched } = await openStockPage(SUMMARY);
  assert.match(html, /<h2[^>]*>[^<]*AI[^<]*<\/h2>|<section[^>]*ai-summary/i);
  assert.ok(!fetched.some((f) => /note/i.test(f)), fetched.join(", "));
  assert.ok(!/<[^>]*notes/i.test(html.split("AI-generated")[1] || ""), "no notes section inside the AI section");
});

test("REQ-43-5: no summary file shows a short note and the rest of the page still works", async () => {
  const { html } = await openStockPage(undefined);
  assert.match(html, /no summary/i);
  assert.ok(html.includes("Alpha"));
  assert.ok(html.includes("Quarterly financials"));
  assert.ok(!html.includes("Strengths"));
});

test("REQ-43-6: invalid JSON behaves as a missing file, with no error shown", async () => {
  const { html } = await openStockPage("{ not json");
  assert.match(html, /no summary/i);
  assert.ok(html.includes("Quarterly financials"));
  assert.ok(!/error|failed|SyntaxError|Unexpected/i.test(html));
});

test("REQ-43-7: an empty SWOT group shows a dash", async () => {
  const withEmpty = { ...SUMMARY, swot: { ...SUMMARY.swot, threats: [] } };
  const { html } = await openStockPage(withEmpty);
  const threats = html.slice(html.search(/Threats/i));
  assert.ok(threats.includes("–"));
  assert.ok(!threats.includes("Price pressure."));
});

test("REQ-43-8: summary and item text is plain text, not HTML", async () => {
  const evil = {
    ...SUMMARY,
    summary: "Sales <i>rose</i>.",
    swot: { ...SUMMARY.swot, strengths: [item("Margin <b>x</b>.")] },
  };
  const { html } = await openStockPage(evil);
  assert.ok(html.includes("&lt;b&gt;x&lt;/b&gt;"));
  assert.ok(html.includes("&lt;i&gt;rose&lt;/i&gt;"));
  assert.ok(!html.includes("<b>x</b>"));
  assert.ok(!html.includes("<i>rose</i>"));
});
