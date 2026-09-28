// Overview: all stocks with price, change today, P/E, dividend yield and quote time, plus the latest news.

async function init() {
  const app = document.getElementById("app");
  let companies, quotesFile, updates;
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

  if (quotesFile.updated_at) {
    document.getElementById("updated").textContent =
      "Prices updated " + fmtTime(quotesFile.updated_at);
  }
  const names = Object.fromEntries(companies.map((c) => [c.ticker, c.name]));

  const rows = companies
    .map((c) => {
      const q = quotesFile.quotes[c.ticker] || {};
      const href = "stock.html?t=" + encodeURIComponent(c.ticker);
      return `<tr>
        <td><a href="${href}">${esc(c.name)}</a> <span class="muted">${esc(c.ticker)}</span></td>
        <td>${fmtNum(q.price, 2, 2)} <span class="muted">${esc(q.currency || c.currency)}</span></td>
        <td>${fmtChange(q.change_pct)}</td>
        <td>${fmtNum(q.pe, 1, 1)}</td>
        <td>${fmtPct(q.dividend_yield, 2)}</td>
        <td class="muted">${fmtTime(q.quote_time)}</td>
      </tr>`;
    })
    .join("");

  app.innerHTML = `
    <h1>My stocks</h1>
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th>Stock</th><th>Price</th><th>Today</th><th>P/E</th><th>Dividend yield</th><th>Quote time</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    ${renderNews(updates[0], names)}`;
}

function renderNews(update, names) {
  if (!update) return "";
  const items = update.items
    .map((item) => {
      const url = safeUrl(item.url);
      const link = url ? ` <a href="${esc(url)}" rel="noopener">Source</a>` : "";
      return `<li><strong>${esc(names[item.ticker] || item.ticker)}:</strong> ${esc(item.text)}${link}</li>`;
    })
    .join("");
  return `
    <h2>News this week <span class="muted">(${fmtDate(update.date)})</span></h2>
    <div class="card">
      <p>${esc(update.summary)}</p>
      ${items ? `<ul>${items}</ul>` : ""}
    </div>`;
}

init();
