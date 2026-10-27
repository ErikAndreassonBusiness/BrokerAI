// Shared helpers for the overview and stock pages. The site only reads the JSON files in data/.

const LOCALE = "sv-SE";

async function loadJSON(path, fallback) {
  const res = await fetch(path + "?v=" + Date.now(), { cache: "no-store" });
  if (res.status === 404 && fallback !== undefined) return fallback;
  if (!res.ok) throw new Error(path + " " + res.status);
  return res.json();
}

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
  return /^https:\/\//i.test(u || "") ? u : null;
}

const isNum = (v) => typeof v === "number" && isFinite(v);

// Numbers in Swedish format with up to `max` decimals; missing values become "–".
function fmtNum(v, max = 1, min = 0) {
  return isNum(v)
    ? v.toLocaleString(LOCALE, {
        minimumFractionDigits: min,
        maximumFractionDigits: max,
      })
    : "–";
}

// A value that is already in percent (3.04 = 3,04 %).
function fmtPct(v, digits = 1) {
  return isNum(v) ? fmtNum(v, digits, digits) + " %" : "–";
}

function fmtDate(d) {
  if (!d) return "–";
  const dt = new Date(d + "T12:00:00");
  return isNaN(dt)
    ? esc(d)
    : dt.toLocaleDateString(LOCALE, {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
}

// ISO timestamps (quote times) in Swedish time.
function fmtTime(iso) {
  if (!iso) return "–";
  const dt = new Date(iso);
  return isNaN(dt)
    ? "–"
    : dt.toLocaleString(LOCALE, {
        timeZone: "Europe/Stockholm",
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
}

// A change in percent (1.5 = +1,50 %), green or red. The colour and sign follow the rounded value,
// so a change that rounds to zero is a plain "0,00 %".
function fmtChange(v, digits = 2) {
  if (!isNum(v)) return "–";
  const rounded = Number(v.toFixed(digits));
  if (rounded === 0) return fmtPct(0, digits);
  const cls = rounded > 0 ? "up" : "down";
  const sign = rounded > 0 ? "+" : "";
  return `<span class="${cls}">${sign}${fmtPct(rounded, digits)}</span>`;
}

// " Source" link for a news item; nothing if the URL isn't https.
function sourceLink(u) {
  const url = safeUrl(u);
  return url ? ` <a href="${esc(url)}" rel="noopener">Source</a>` : "";
}

function showError(el, e) {
  el.innerHTML = `<p class="card">Could not load the data (${esc(e.message)}).</p>`;
}
