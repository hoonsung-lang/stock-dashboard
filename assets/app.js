/* 2026 글로벌 주가 대시보드 */
"use strict";

const PAGE = 50;
const MKT_LABEL = { US: "🇺🇸 미국", KR: "🇰🇷 한국", JP: "🇯🇵 일본" };

const state = {
  all: [],
  view: [],
  market: "ALL",
  query: "",
  sortKey: "r_cur",
  sortDir: -1, // -1 내림차순
  shown: PAGE,
  selected: null,
  dates: {},
};

const $ = (s) => document.querySelector(s);

/* ---------- 유틸 ---------- */
function fmtPrice(v, market) {
  if (v == null) return "—";
  if (market === "KR" || market === "JP") return Math.round(v).toLocaleString();
  return v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtPct(v) {
  if (v == null) return "—";
  const s = v > 0 ? "+" : "";
  return `${s}${v.toFixed(2)}%`;
}
function cls(v) { return v == null ? "flat" : v > 0 ? "up" : v < 0 ? "down" : "flat"; }

/* 검색어를 ';' 로 분리 → 다중 검색어 배열 (소문자, 공백/빈값 제거) */
function parseTerms(q) {
  return (q || "")
    .split(";")
    .map((t) => t.trim().toLowerCase())
    .filter(Boolean);
}

/* ---------- 데이터 로드 ---------- */
async function load() {
  try {
    const res = await fetch("data/data.json?_=" + Date.now());
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();
    state.all = data.stocks || [];
    state.dates = data.dates || {};
    renderMeta(data);
    renderLegend(data);
    apply();
  } catch (e) {
    $("#meta").textContent = "데이터를 불러오지 못했습니다. (data/data.json 생성 대기 중일 수 있습니다)";
    console.error(e);
  }
}

function renderMeta(data) {
  const n = (data.stocks || []).length.toLocaleString();
  const gen = data.generated_at ? new Date(data.generated_at).toLocaleString("ko-KR") : "—";
  $("#meta").textContent = `총 ${n}개 종목 · 갱신 ${gen}`;
}

function renderLegend(data) {
  const d = data.labels || {};
  const fmt = (x) => (x ? x : "—");
  const pills = [
    ["개장일", fmt(d.open)],
    ["2개월말", fmt(d.m2)],
    ["4개월말", fmt(d.m4)],
    ["현재", fmt(d.current)],
  ];
  $("#legend").innerHTML = pills
    .map(([k, v]) => `<span class="pill">${k} <b>${v}</b></span>`)
    .join("") +
    `<span class="pill" style="border-color:var(--up);color:var(--up)">▲ 상승</span>` +
    `<span class="pill" style="border-color:var(--down);color:var(--down)">▼ 하락</span>`;
}

/* ---------- 필터/정렬 ---------- */
function apply() {
  const terms = parseTerms(state.query);
  let v = state.all.filter((s) => {
    if (state.market !== "ALL" && s.market !== state.market) return false;
    if (terms.length) {
      const hay = (s.ticker + " " + s.name).toLowerCase();
      // ';' 로 이어진 여러 검색어 중 하나라도 일치하면 포함 (OR)
      if (!terms.some((t) => hay.includes(t))) return false;
    }
    return true;
  });
  const k = state.sortKey, dir = state.sortDir;
  v.sort((a, b) => {
    let av = a[k], bv = b[k];
    if (k === "name" || k === "market") {
      av = (av || "").toString(); bv = (bv || "").toString();
      return av.localeCompare(bv) * dir;
    }
    if (av == null) return 1;
    if (bv == null) return -1;
    return (av - bv) * dir;
  });
  state.view = v;
  state.shown = PAGE;
  renderRows();
}

/* ---------- 테이블 렌더 ---------- */
function renderRows() {
  const tb = $("#rows");
  const rows = state.view.slice(0, state.shown);
  $("#empty").hidden = state.view.length !== 0;
  tb.innerHTML = rows.map((s, i) => {
    const sub = s.submarket ? `<small>${s.submarket} · ${s.ticker}</small>` : `<small>${s.ticker}</small>`;
    return `<tr data-tk="${s.ticker}" data-mkt="${s.market}">
      <td class="t-rank">${i + 1}</td>
      <td><div class="nm">${esc(s.name)}${sub}</div></td>
      <td><span class="mkt-badge">${MKT_LABEL[s.market] || s.market}</span></td>
      <td class="num">${fmtPrice(s.p_open, s.market)}</td>
      <td class="num">${fmtPrice(s.p_m2, s.market)}</td>
      <td class="num ${cls(s.r_m2)}">${fmtPct(s.r_m2)}</td>
      <td class="num">${fmtPrice(s.p_m4, s.market)}</td>
      <td class="num ${cls(s.r_m4)}">${fmtPct(s.r_m4)}</td>
      <td class="num">${fmtPrice(s.p_cur, s.market)}</td>
      <td class="num ${cls(s.r_cur)}"><b>${fmtPct(s.r_cur)}</b></td>
    </tr>`;
  }).join("");
  $("#more").hidden = state.view.length <= state.shown;
}

function esc(s) {
  return (s || "").replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

/* ---------- 상세 카드 ---------- */
function showDetail(stock) {
  state.selected = stock;
  const cells = [
    ["개장일", stock.p_open, null, mdate(stock.market, "open")],
    ["2개월말", stock.p_m2, stock.r_m2, mdate(stock.market, "m2")],
    ["4개월말", stock.p_m4, stock.r_m4, mdate(stock.market, "m4")],
    ["현재", stock.p_cur, stock.r_cur, mdate(stock.market, "current")],
  ];
  const sub = stock.submarket ? `<span class="d-badge">${stock.submarket}</span>` : "";
  $("#detail").innerHTML = `
    <div class="d-head">
      <span class="d-name">${esc(stock.name)}</span>
      <span class="d-tk">${stock.ticker}</span>
      <span class="d-badge">${MKT_LABEL[stock.market] || stock.market}</span>${sub}
      <button class="d-close" id="dclose">닫기 ✕</button>
    </div>
    <div class="d-grid">
      ${cells.map(([lbl, p, r, dt]) => `
        <div class="d-cell">
          <div class="lbl">${lbl}</div>
          <div class="date">${dt || ""}</div>
          <div class="price">${fmtPrice(p, stock.market)}</div>
          <div class="chg ${cls(r)}">${r == null ? "기준" : fmtPct(r)}</div>
        </div>`).join("")}
    </div>`;
  $("#detail").hidden = false;
  $("#dclose").onclick = () => { $("#detail").hidden = true; state.selected = null; };
  $("#detail").scrollIntoView({ behavior: "smooth", block: "nearest" });
}
function mdate(market, key) {
  return (state.dates[market] && state.dates[market][key]) || "";
}

/* ---------- 자동완성 ---------- */
function suggest(q) {
  const box = $("#suggest");
  // 다중 검색(';' 포함) 모드에서는 표에 모두 나열되므로 자동완성 숨김
  if ((q || "").includes(";")) { box.hidden = true; return; }
  q = q.trim().toLowerCase();
  if (!q) { box.hidden = true; return; }
  const hits = state.all
    .filter((s) => (s.ticker + " " + s.name).toLowerCase().includes(q))
    .filter((s) => state.market === "ALL" || s.market === state.market)
    .slice(0, 8);
  if (!hits.length) { box.hidden = true; return; }
  box.innerHTML = hits.map((s) =>
    `<li data-tk="${s.ticker}" data-mkt="${s.market}">
       <span class="s-name">${esc(s.name)}</span>
       <span class="s-tk">${MKT_LABEL[s.market] || s.market} · ${s.ticker} · ${fmtPct(s.r_cur)}</span>
     </li>`).join("");
  box.hidden = false;
}

/* ---------- 이벤트 ---------- */
function init() {
  $("#search").addEventListener("input", (e) => {
    state.query = e.target.value;
    suggest(state.query);
    apply();
  });
  $("#search").addEventListener("blur", () =>
    setTimeout(() => ($("#suggest").hidden = true), 150));
  $("#clear").addEventListener("click", () => {
    $("#search").value = ""; state.query = "";
    $("#suggest").hidden = true; apply();
  });

  $("#suggest").addEventListener("mousedown", (e) => {
    const li = e.target.closest("li");
    if (!li) return;
    const s = state.all.find((x) => x.ticker === li.dataset.tk && x.market === li.dataset.mkt);
    if (s) { $("#search").value = s.name; state.query = s.name; apply(); showDetail(s); }
    $("#suggest").hidden = true;
  });

  $("#tabs").addEventListener("click", (e) => {
    const b = e.target.closest(".tab");
    if (!b) return;
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    b.classList.add("active");
    state.market = b.dataset.market;
    apply();
  });

  document.querySelectorAll("thead th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const k = th.dataset.sort;
      if (state.sortKey === k) state.sortDir *= -1;
      else { state.sortKey = k; state.sortDir = (k === "name" || k === "market") ? 1 : -1; }
      document.querySelectorAll("thead th").forEach((t) => t.classList.remove("active"));
      th.classList.add("active");
      apply();
    });
  });

  $("#rows").addEventListener("click", (e) => {
    const tr = e.target.closest("tr");
    if (!tr) return;
    const s = state.all.find((x) => x.ticker === tr.dataset.tk && x.market === tr.dataset.mkt);
    if (s) showDetail(s);
  });

  $("#moreBtn").addEventListener("click", () => {
    state.shown += PAGE; renderRows();
  });

  load();
}

document.addEventListener("DOMContentLoaded", init);
