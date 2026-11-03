// Tests for the CEO letter comparison section on the stock page (issue #53, ADR 0004).
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
const TITLE = "CEO letter comparison";

const comparison = (period, compared_to, extra = {}) => ({
  period,
  compared_to,
  source_url: `https://example.com/${period}.pdf`,
  tone: { previous: "neutral", current: "positive" },
  dropped_topics: [`Dropped ${period}`],
  new_topics: [`New ${period}`],
  changed_wording: [{ topic: `Topic ${period}`, before: `old ${period}`, after: `fresh ${period}` }],
  summary: `Summary ${period}.`,
  ...extra,
});
const Q2 = comparison("2026-Q2", "2026-Q1", { tone: { previous: "negative", current: "neutral" } });
const Q3 = comparison("2026-Q3", "2026-Q2", { tone: { previous: "neutral", current: "positive" } });
const LETTERS = {
  ticker: "A.ST",
  comparisons: [Q2, Q3],
  trend: { from: "2026-Q2", to: "2026-Q3", summary: "Trend: ever more positive." },
};

// letters: a JSON value, or undefined for a missing file (404).
async function openStockPage(letters) {
  const fetched = [];
  const files = {
    "data/companies.json": [COMPANY],
    "data/quotes.json": { quotes: {} },
    "data/updates.json": [],
    "data/financials/A.ST.json": { ticker: "A.ST", currency: "SEK", quarters: [] },
  };
  if (letters !== undefined) files["data/ceo_letters/A.ST.json"] = letters;
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
      return { ok: true, status: 200, json: async () => body };
    },
  });
  vm.runInContext(src, context);
  for (let i = 0; i < 50 && app.innerHTML === "Loading"; i++) await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
  return { html: app.innerHTML, fetched };
}

// The section: from its title to the next <h2> or the end of the page.
function section(html) {
  const start = html.indexOf(TITLE);
  if (start < 0) return "";
  const rest = html.slice(start + TITLE.length);
  const end = rest.indexOf("<h2");
  return TITLE + (end >= 0 ? rest.slice(0, end) : rest);
}
const text = (html) => html.replace(/<[^>]*>/g, " ");

// Splits the section into the <details> blocks and tells which are open.
function detailsBlocks(html) {
  return [...html.matchAll(/<details([^>]*)>([\s\S]*?)<\/details>/g)].map((m) => ({
    open: /\bopen\b/.test(m[1]),
    html: m[2],
  }));
}

test("REQ-53-1: the section is shown, labelled AI-generated", async () => {
  const { html, fetched } = await openStockPage(LETTERS);
  assert.ok(fetched.includes("data/ceo_letters/A.ST.json"));
  const s = section(html);
  assert.ok(s, "section title is on the page");
  assert.ok(s.includes("AI-generated"));
});

test("REQ-53-2: the latest comparison shows tone, topics, wording changes, summary and report link", async () => {
  const s = section((await openStockPage(LETTERS)).html);
  assert.match(text(s), /neutral\s*→\s*positive/);
  for (const t of ["Dropped 2026-Q3", "New 2026-Q3", "Topic 2026-Q3", "Summary 2026-Q3."]) assert.ok(s.includes(t), t);
  assert.match(text(s), /old 2026-Q3\s*→\s*fresh 2026-Q3/);
  const link = s.match(/<a [^>]*href="https:\/\/example\.com\/2026-Q3\.pdf"[^>]*>/);
  assert.ok(link, "link to source_url");
  assert.match(link[0], /target="_blank"/);
  assert.match(link[0], /rel="[^"]*noopener/);
});

test("REQ-53-3: the trend summary, its period and the tone of each quarter oldest to newest", async () => {
  const s = section((await openStockPage(LETTERS)).html);
  assert.ok(s.includes("Trend: ever more positive."));
  assert.ok(s.includes("2026-Q2") && s.includes("2026-Q3"));
  const row = s.slice(s.indexOf("Trend: ever more positive."));
  const q2 = row.indexOf("2026-Q2");
  const q3 = row.indexOf("2026-Q3");
  assert.ok(q2 >= 0 && q3 > q2, "Q2 left of Q3");
  assert.ok(row.slice(q2, q3).includes("neutral"), "tone of Q2 (current) next to Q2");
  assert.ok(row.slice(q3).includes("positive"), "tone of Q3 (current) next to Q3");
});

test("REQ-53-3: without a trend there is no trend summary", async () => {
  const { trend, ...noTrend } = LETTERS;
  const s = section((await openStockPage(noTrend)).html);
  assert.ok(s);
  assert.ok(!s.includes("Trend: ever more positive."));
});

test("REQ-53-4: only the latest comparison is open; older ones are collapsed", async () => {
  const s = section((await openStockPage(LETTERS)).html);
  const blocks = detailsBlocks(s);
  const latest = blocks.find((b) => b.html.includes("Summary 2026-Q3."));
  const older = blocks.find((b) => b.html.includes("Summary 2026-Q2."));
  assert.ok(older, "the older comparison is in a <details>");
  assert.equal(older.open, false);
  assert.ok(!latest || latest.open, "the latest is open (or not inside a <details>)");
  assert.ok(!detailsBlocks(s).some((b) => b !== older && !b.open && b.html.includes("Summary 2026-Q3.")));
});

test("REQ-53-5: no letter file means no section", async () => {
  const { html } = await openStockPage(undefined);
  assert.ok(!html.includes(TITLE));
  assert.ok(html.includes("Quarterly financials"), "rest of the page still works");
});

test("REQ-53-6: empty topic and wording lists show a dash", async () => {
  const empty = comparison("2026-Q3", "2026-Q2", { dropped_topics: [], new_topics: [], changed_wording: [] });
  const s = section((await openStockPage({ ticker: "A.ST", comparisons: [empty] })).html);
  assert.ok(s.includes("Summary 2026-Q3."));
  assert.ok((text(s).match(/–/g) || []).length >= 3, "a dash for each of the three empty lists");
  assert.ok(!/<ul[^>]*>\s*<\/ul>/.test(s), "no empty list block");
});

test("REQ-53-7: only data/ceo_letters is read, never private/, and text is escaped", async () => {
  const evil = comparison("2026-Q3", "2026-Q2", {
    dropped_topics: ["<b>x</b>"],
    new_topics: ["<u>n</u>"],
    changed_wording: [{ topic: "<i>t</i>", before: "<s>b</s>", after: "<em>a</em>" }],
    summary: "Sum <strong>m</strong>.",
  });
  const { html, fetched } = await openStockPage({
    ticker: "A.ST",
    comparisons: [evil],
    trend: { from: "2026-Q3", to: "2026-Q3", summary: "Tr <mark>t</mark>" },
  });
  assert.ok(fetched.includes("data/ceo_letters/A.ST.json"));
  assert.ok(!fetched.some((f) => /private/i.test(f)), fetched.join(", "));
  const s = section(html);
  for (const tag of ["b", "u", "i", "s", "em", "strong", "mark"]) {
    assert.ok(!s.includes(`<${tag}>`), `<${tag}> not rendered as HTML`);
  }
  assert.ok(s.includes("&lt;b&gt;x&lt;/b&gt;"));
  assert.ok(s.includes("&lt;strong&gt;m&lt;/strong&gt;"));
});

test("REQ-53-8: the section has no score, rating or recommendation", async () => {
  const s = text(section((await openStockPage(LETTERS)).html));
  assert.ok(s.length > TITLE.length, "the section exists");
  assert.ok(!/\b(score|rating|recommend\w*|buy|sell|hold)\b/i.test(s), s);
});

test("robustness: null entries and missing wording fields do not break the page", async () => {
  const bad = comparison("2026-Q3", "2026-Q2", {
    dropped_topics: [null, "Kept topic"],
    changed_wording: [null, { topic: "T", after: "only after" }],
  });
  const { html } = await openStockPage({ ticker: "A.ST", comparisons: [null, bad] });
  assert.ok(html.includes("Quarterly financials"));
  const s = section(html);
  assert.ok(s.includes("Kept topic"));
  assert.ok(!/undefined|null/.test(s));
  assert.match(text(s), /–\s*→\s*only after/);
});

test("ordering: the latest comparison is the newest period, whatever the file order", async () => {
  const s = section((await openStockPage({ ticker: "A.ST", comparisons: [Q3, Q2] })).html);
  const older = detailsBlocks(s).find((b) => b.html.includes("Summary 2026-Q2."));
  assert.ok(older && !older.open);
  assert.ok(!detailsBlocks(s).some((b) => b.html.includes("Summary 2026-Q3.")));
});
