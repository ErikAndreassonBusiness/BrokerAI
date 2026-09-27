// Stock Tracker: a static site that reads JSON files from /data.
// The weekly Claude agent updates those files; this page only displays them.

const app = document.getElementById("app");
const tip = document.getElementById("tip");
const LOCALE = "sv-SE";

const state = { companies: [], reports: [], updates: [] };

// ---------- data ----------
async function loadJSON(path) {
  const res = await fetch(path + "?v=" + Date.now(), { cache: "no-store" });
  if (!res.ok) throw new Error(path + " " + res.status);
  return res.json();
}

async function init() {
  try {
    const [companies, reports, updates] = await Promise.all([
      loadJSON("data/companies.json"),
      loadJSON("data/reports.json"),
      loadJSON("data/updates.json"),
    ]);
    Object.assign(state, { companies, reports, updates });
  } catch (e) {
    app.innerHTML = `<p class="card">Could not load the data files (${esc(e.message)}).</p>`;
    return;
  }
  const last = state.updates[0];
  document.getElementById("last-run").textContent = last
    ? `Agent last ran ${fmtDate(last.date)}`
    : "";
  window.addEventListener("hashchange", route);
  route();
}

// ---------- helpers ----------
function esc(s) {
  return String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
}
function safeUrl(u) {
  return /^https?:\/\//i.test(u || "") ? u : null;
}
const isNum = (v) => typeof v === "number" && isFinite(v);
function fmtNum(v, digits = 0) {
  return isNum(v)
    ? v.toLocaleString(LOCALE, {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      })
    : "–";
}
function fmtPct(v, digits = 1) {
  return isNum(v) ? fmtNum(v * 100, digits) + " %" : "–";
}
function fmtDate(d) {
  if (!d) return "–";
  const dt = new Date(d + "T12:00:00");
  return isNaN(dt)
    ? d
    : dt.toLocaleDateString(LOCALE, {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
}
function margin(r) {
  return isNum(r.ebit) && isNum(r.revenue) && r.revenue !== 0
    ? r.ebit / r.revenue
    : null;
}
function parsePeriod(p) {
  const m = /^(\d{4})-Q([1-4])$/.exec(p || "");
  return m ? { y: +m[1], q: +m[2] } : null;
}
function periodKey(p) {
  const x = parsePeriod(p);
  return x ? x.y * 10 + x.q : 0;
}
function reportsFor(id) {
  return state.reports
    .filter((r) => r.company === id)
    .sort((a, b) => periodKey(a.period) - periodKey(b.period));
}
function sameQuarterLastYear(list, r) {
  const p = parsePeriod(r.period);
  return p ? list.find((x) => x.period === `${p.y - 1}-Q${p.q}`) : null;
}
function change(cur, prev) {
  if (!isNum(cur) || !isNum(prev) || prev === 0) return null;
  return (cur - prev) / Math.abs(prev);
}
function chg(v) {
  if (v === null) return "";
  const cls = v >= 0 ? "up" : "down";
  const arrow = v >= 0 ? "▲" : "▼";
  return `<span class="chg ${cls}" title="vs. same quarter last year">${arrow} ${fmtPct(Math.abs(v), 0)}</span>`;
}
function company(id) {
  return state.companies.find((c) => c.id === id);
}

// ---------- routing ----------
function route() {
  hideTip();
  const m = /^#\/c\/(.+)$/.exec(location.hash);
  if (m && company(decodeURIComponent(m[1])))
    renderCompany(decodeURIComponent(m[1]));
  else renderOverview();
  window.scrollTo(0, 0);
}

// ---------- overview ----------
function renderOverview() {
  if (!state.companies.length) {
    app.innerHTML = `<div class="card empty"><h1>No companies yet</h1>
      <p class="muted">Add your stocks to <code>data/companies.json</code>. The agent fills in the reports on its next run.</p></div>`;
    return;
  }

  const latest = state.updates[0];
  let news = "";
  if (latest) {
    const items = (latest.items || [])
      .map((i) => {
        const c = company(i.company);
        const url = safeUrl(i.url);
        return `<li>${c ? `<strong>${esc(c.name)}:</strong> ` : ""}${esc(i.text)}${url ? ` <a href="${esc(url)}" target="_blank" rel="noopener">source</a>` : ""}</li>`;
      })
      .join("");
    news = `<section class="card news" style="margin-top:16px">
      <h3>This week · ${fmtDate(latest.date)}</h3>
      <div>${esc(latest.summary)}</div>
      ${items ? `<ul>${items}</ul>` : ""}
    </section>`;
  }

  const rows = state.companies
    .map((c) => {
      const list = reportsFor(c.id);
      const r = list[list.length - 1];
      if (!r) {
        return `<tr class="link" tabindex="0" data-id="${esc(c.id)}"><td><strong>${esc(c.name)}</strong> <span class="muted">${esc(c.ticker || "")}</span></td>
        <td colspan="6" class="muted" style="text-align:left">No reports yet</td></tr>`;
      }
      const prev = sameQuarterLastYear(list, r);
      return `<tr class="link" tabindex="0" data-id="${esc(c.id)}">
      <td><strong>${esc(c.name)}</strong> <span class="muted">${esc(c.ticker || "")}</span></td>
      <td>${esc(r.period)}</td>
      <td>${fmtNum(r.revenue)}${chg(change(r.revenue, prev?.revenue))}</td>
      <td>${fmtNum(r.ebit)}${chg(change(r.ebit, prev?.ebit))}</td>
      <td>${fmtPct(margin(r))}</td>
      <td>${fmtNum(r.eps, 2)}${chg(change(r.eps, prev?.eps))}</td>
      <td>${fmtDate(r.report_date)}</td>
    </tr>`;
    })
    .join("");

  app.innerHTML = `
    ${news}
    <h2>Latest quarter per company</h2>
    <div class="table-wrap"><table>
      <thead><tr><th>Company</th><th>Quarter</th><th>Revenue (m)</th><th>EBIT (m)</th><th>EBIT margin</th><th>EPS</th><th>Reported</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>
    <p class="muted" style="font-size:13px">Amounts in millions of each company's reporting currency. Arrows compare with the same quarter last year. Click a company for history.</p>
    ${
      state.updates.length > 1
        ? `<h2>Earlier updates</h2>` +
          state.updates
            .slice(1, 8)
            .map(
              (u) =>
                `<p><strong>${fmtDate(u.date)}</strong> · ${esc(u.summary)}</p>`,
            )
            .join("")
        : ""
    }
  `;

  app.querySelectorAll("tr.link").forEach((tr) => {
    const go = () => {
      location.hash = "#/c/" + encodeURIComponent(tr.dataset.id);
    };
    tr.addEventListener("click", go);
    tr.addEventListener("keydown", (e) => {
      if (e.key === "Enter") go();
    });
  });
}

// ---------- company page ----------
function renderCompany(id) {
  const c = company(id);
  const list = reportsFor(id);
  const last = list[list.length - 1];
  const cur = last?.currency || c.currency || "";
  const ir = safeUrl(c.ir_url);

  let body;
  if (!list.length) {
    body = `<div class="card empty"><p class="muted">No reports stored for ${esc(c.name)} yet.</p></div>`;
  } else {
    const recent = list.slice(-12);
    const tableRows = [...list]
      .reverse()
      .map((r) => {
        const prev = sameQuarterLastYear(list, r);
        const src = safeUrl(r.source_url);
        return `<tr>
        <td>${esc(r.period)}</td>
        <td>${fmtNum(r.revenue)}${chg(change(r.revenue, prev?.revenue))}</td>
        <td>${fmtNum(r.ebit)}${chg(change(r.ebit, prev?.ebit))}</td>
        <td>${fmtPct(margin(r))}</td>
        <td>${fmtNum(r.net_income)}</td>
        <td>${fmtNum(r.eps, 2)}</td>
        <td>${fmtNum(r.operating_cash_flow)}</td>
        <td>${fmtNum(r.net_debt)}</td>
        <td>${src ? `<a href="${esc(src)}" target="_blank" rel="noopener">Report</a>` : "–"}</td>
      </tr>`;
      })
      .join("");

    const hl = (last.highlights || [])
      .map((h) => `<li>${esc(h)}</li>`)
      .join("");
    body = `
      <section class="grid" style="margin-top:16px">
        <div class="card">
          <h3>Latest: ${esc(last.period)} <span class="muted">· reported ${fmtDate(last.report_date)}</span></h3>
          ${hl ? `<ul class="plain">${hl}</ul>` : '<p class="muted">No highlights noted.</p>'}
        </div>
        <div class="card">
          <h3>Outlook / guidance</h3>
          <p style="margin:0">${last.guidance ? esc(last.guidance) : '<span class="muted">No guidance given.</span>'}</p>
          ${isNum(last.dividend_per_share) ? `<p style="margin:8px 0 0"><span class="pill">Dividend</span>${fmtNum(last.dividend_per_share, 2)} ${esc(cur)}/share</p>` : ""}
        </div>
      </section>
      <h2>Per quarter</h2>
      <section class="grid">
        <div class="card chart"><h3>Revenue (m ${esc(cur)})</h3>${barChart(recent, "revenue", (v) => fmtNum(v) + " m")}</div>
        <div class="card chart"><h3>EBIT (m ${esc(cur)})</h3>${barChart(recent, "ebit", (v) => fmtNum(v) + " m")}</div>
        <div class="card chart"><h3>EBIT margin</h3>${lineChart(recent, margin, (v) => fmtPct(v))}</div>
        <div class="card chart"><h3>Earnings per share (${esc(cur)})</h3>${barChart(recent, "eps", (v) => fmtNum(v, 2))}</div>
      </section>
      <h2>All quarters</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Quarter</th><th>Revenue</th><th>EBIT</th><th>Margin</th><th>Net income</th><th>EPS</th><th>Op. cash flow</th><th>Net debt</th><th>Source</th></tr></thead>
        <tbody>${tableRows}</tbody>
      </table></div>
      <p class="muted" style="font-size:13px">Amounts in millions of ${esc(cur)}, except EPS.</p>`;
  }

  app.innerHTML = `
    <a class="back" href="#/">← All companies</a>
    <h1>${esc(c.name)}</h1>
    <div><span class="pill">${esc(c.ticker || "")}</span>${ir ? `<a href="${esc(ir)}" target="_blank" rel="noopener">Investor relations</a>` : ""}</div>
    ${body}`;
  bindTips();
}

// ---------- charts (plain SVG) ----------
const W = 360,
  H = 190,
  PAD = { l: 48, r: 8, t: 10, b: 26 };

function scaleY(values) {
  let min = Math.min(0, ...values),
    max = Math.max(0, ...values);
  if (min === max) max = min + 1;
  const step = niceStep((max - min) / 4);
  min = Math.floor(min / step) * step;
  max = Math.ceil(max / step) * step;
  const ticks = [];
  for (let v = min; v <= max + step / 2; v += step) ticks.push(v);
  const y = (v) => PAD.t + (H - PAD.t - PAD.b) * (1 - (v - min) / (max - min));
  return { y, ticks };
}
function niceStep(raw) {
  const p = Math.pow(10, Math.floor(Math.log10(raw || 1)));
  const n = raw / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10) * p;
}
function shortNum(v) {
  const a = Math.abs(v);
  // chart values are in millions, so 1 000 m = 1 bn
  if (a >= 1e3) return fmtNum(v / 1e3, a >= 1e4 ? 0 : 1) + " bn";
  return fmtNum(v, a < 10 && v % 1 ? 1 : 0);
}
function axes(ticks, y, labels, x, fmtTick) {
  const grid = ticks
    .map(
      (
        t,
      ) => `<line class="${t === 0 ? "zero" : "gridline"}" x1="${PAD.l}" x2="${W - PAD.r}" y1="${y(t)}" y2="${y(t)}"/>
    <text class="axis" x="${PAD.l - 6}" y="${y(t) + 4}" text-anchor="end">${fmtTick(t)}</text>`,
    )
    .join("");
  const every = Math.ceil(labels.length / 6);
  // label every n-th quarter, counted back from the newest so the latest is always labelled
  const xl = labels
    .map((l, i) =>
      (labels.length - 1 - i) % every === 0
        ? `<text class="axis" x="${x(i)}" y="${H - 8}" text-anchor="middle">${esc(l.replace("-", " "))}</text>`
        : "",
    )
    .join("");
  return grid + xl;
}

function barChart(list, key, fmt) {
  const pts = list
    .map((r) => ({ label: r.period, v: r[key] }))
    .filter((p) => isNum(p.v));
  if (pts.length < 1) return '<p class="muted">No data.</p>';
  const { y, ticks } = scaleY(pts.map((p) => p.v));
  const band = (W - PAD.l - PAD.r) / pts.length;
  const bw = Math.min(28, band - 2);
  const x = (i) => PAD.l + band * i + band / 2;
  const bars = pts
    .map((p, i) => {
      const y0 = y(0),
        y1 = y(p.v);
      const top = Math.min(y0, y1),
        h = Math.max(1, Math.abs(y1 - y0));
      const r = Math.min(4, bw / 2, h);
      // rounded data-end, square at the baseline
      const xL = x(i) - bw / 2,
        xR = x(i) + bw / 2;
      const d =
        p.v >= 0
          ? `M${xL},${y0} V${top + r} Q${xL},${top} ${xL + r},${top} H${xR - r} Q${xR},${top} ${xR},${top + r} V${y0} Z`
          : `M${xL},${y0} V${top + h - r} Q${xL},${top + h} ${xL + r},${top + h} H${xR - r} Q${xR},${top + h} ${xR},${top + h - r} V${y0} Z`;
      return `<g class="col" data-tip="${esc(p.label)}: ${esc(fmt(p.v))}">
      <path class="bar${p.v < 0 ? " neg" : ""}" d="${d}"/>
      <rect class="hit" x="${PAD.l + band * i}" y="${PAD.t}" width="${band}" height="${H - PAD.t - PAD.b}"/></g>`;
    })
    .join("");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(key)} per quarter">
    ${axes(
      ticks,
      y,
      pts.map((p) => p.label),
      x,
      shortNum,
    )}${bars}</svg>`;
}

function lineChart(list, fn, fmt) {
  const pts = list
    .map((r) => ({ label: r.period, v: fn(r) }))
    .filter((p) => isNum(p.v));
  if (pts.length < 1) return '<p class="muted">No data.</p>';
  const { y, ticks } = scaleY(pts.map((p) => p.v));
  const band = (W - PAD.l - PAD.r) / pts.length;
  const x = (i) => PAD.l + band * i + band / 2;
  const path = pts.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.v)}`).join(" ");
  const dots = pts
    .map(
      (p, i) => `<g data-tip="${esc(p.label)}: ${esc(fmt(p.v))}">
      <circle class="dot" cx="${x(i)}" cy="${y(p.v)}" r="4"/>
      <rect class="hit" x="${PAD.l + band * i}" y="${PAD.t}" width="${band}" height="${H - PAD.t - PAD.b}"/></g>`,
    )
    .join("");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Margin per quarter">
    ${axes(
      ticks,
      y,
      pts.map((p) => p.label),
      x,
      (t) => fmtNum(t * 100, 0) + "%",
    )}
    <path class="line" d="${path}"/>${dots}</svg>`;
}

// ---------- tooltips ----------
function bindTips() {
  app.querySelectorAll("[data-tip]").forEach((el) => {
    el.addEventListener("mousemove", (e) =>
      showTip(el.dataset.tip, e.clientX, e.clientY),
    );
    el.addEventListener("mouseleave", hideTip);
    el.addEventListener(
      "touchstart",
      (e) => {
        const t = e.touches[0];
        showTip(el.dataset.tip, t.clientX, t.clientY);
      },
      { passive: true },
    );
  });
}
function showTip(text, cx, cy) {
  tip.textContent = text;
  tip.hidden = false;
  const w = tip.offsetWidth;
  tip.style.left = Math.min(window.innerWidth - w - 8, cx + 12) + "px";
  tip.style.top = cy - 36 + "px";
}
function hideTip() {
  tip.hidden = true;
}

init();
