# -*- coding: utf-8 -*-
"""한국 시장 데이터 수집기 — 네이버 증권 비공식 API 기반.

모든 함수는 파이썬 dict/list를 반환한다. KRX 로그인이 필요 없는
m.stock.naver.com / finance.naver.com 엔드포인트만 사용한다.
"""
import re

from common import get_json, get_text, num

API = "https://m.stock.naver.com/api"


# ---------------------------------------------------------------- 지수
def get_index(code="KOSPI"):
    """KOSPI/KOSDAQ 지수 현재가·당일등락·1개월 등락률."""
    j = get_json(f"{API}/index/{code}/basic")
    close = num(j.get("closePrice"))
    return {
        "code": code,
        "close": close,
        "change": num(j.get("compareToPreviousClosePrice")),
        "changeRate": num(j.get("fluctuationsRatio")),
        "chg_1m_pct": _index_chg_1m(code, close),
        "date": j.get("localTradedAt", "")[:10],
    }


def _index_chg_1m(code, close):
    """지수 일별 시세로 1개월(캘린더 30일) 전 종가 대비 등락률(%). 실패 시 None."""
    if not close:
        return None
    try:
        from datetime import datetime, timedelta
        rows = get_json(f"{API}/index/{code}/price?pageSize=30&page=1")
        if not rows:
            return None
        latest = datetime.strptime(rows[0]["localTradedAt"][:10], "%Y-%m-%d")
        cutoff = latest - timedelta(days=30)
        # 30일 전 이하 날짜 중 가장 최근 종가 (없으면 가장 오래된 행)
        ref = next((r for r in rows
                    if datetime.strptime(r["localTradedAt"][:10], "%Y-%m-%d") <= cutoff),
                   rows[-1])
        base = num(ref["closePrice"])
        return round((close / base - 1) * 100, 2) if base else None
    except Exception:
        return None


# ---------------------------------------------------------------- 업종/테마
def _get_groups(kind, max_pages=8):
    """kind: 'industry' | 'theme'. 전체 그룹(업종/테마) 등락률 목록."""
    out = []
    for page in range(1, max_pages + 1):
        j = get_json(f"{API}/stocks/{kind}?page={page}&pageSize=60")
        groups = j.get("groups", [])
        if not groups:
            break
        for g in groups:
            out.append({
                "no": g["no"],
                "name": g["name"],
                "changeRate": num(g.get("changeRate")),
                "riseCount": g.get("riseCount"),
                "fallCount": g.get("fallCount"),
                "totalCount": g.get("totalCount"),
            })
        if len(groups) < 60:
            break
    return out


def get_industries():
    return _get_groups("industry")


def get_themes():
    return _get_groups("theme")


def get_group_stocks(kind, no, page_size=30):
    """업종/테마 내 종목 목록 (등락률·거래대금 포함)."""
    j = get_json(f"{API}/stocks/{kind}/{no}?page=1&pageSize={page_size}")
    out = []
    for s in j.get("stocks", []):
        out.append({
            "code": s["itemCode"],
            "name": s["stockName"],
            "close": num(s.get("closePrice")),
            "changeRate": num(s.get("fluctuationsRatio")),
            "tradingValue_M": num(s.get("accumulatedTradingValue")),  # 백만원
            "marketValue_100M": num(s.get("marketValue")),
        })
    return out


# ---------------------------------------------------------------- 수급
_ETF_PREFIX = ("KODEX", "TIGER", "PLUS", "ACE", "SOL", "RISE", "HANARO",
               "KOSEF", "KIWOOM", "TIME", "WON", "UNICORN", "마이다스", "히어로즈")


def is_etf_like(name):
    n = name.upper()
    return any(n.startswith(p) for p in _ETF_PREFIX)


def get_deal_rank(investor="foreign", trade="buy"):
    """외국인/기관 순매수·순매도 상위 종목 (당일, finance.naver.com iframe HTML).

    investor: 'foreign' | 'organ'  /  trade: 'buy' | 'sell'
    반환 필드: quantity_K(천주), amount_M(백만원), volume(주), is_etf.
    """
    gubun = {"foreign": 9000, "organ": 1000}[investor]
    url = (f"https://finance.naver.com/sise/sise_deal_rank_iframe.naver"
           f"?investor_gubun={gubun}&type={trade}")
    html = get_text(url, encoding="euc-kr")
    rows = re.findall(
        r"code=([0-9A-Z]{6})[^>]*title='([^']+)'[^>]*>.*?"
        r'<td class="number">\s*([\d,\-]+)\s*</td>\s*'
        r'<td class="number">\s*([\d,\-]+)\s*</td>\s*'
        r'<td class="number">\s*([\d,\-]+)\s*</td>',
        html, re.S)
    out = []
    seen = set()
    for code, name, qty, amt, vol in rows:
        if code in seen:
            continue
        seen.add(code)
        name = name.strip()
        out.append({
            "code": code, "name": name,
            "quantity_K": num(qty), "amount_M": num(amt), "volume": num(vol),
            "is_etf": is_etf_like(name),
        })
    return out


def get_investor_trend(code, size=20):
    """종목별 일자별 외국인/기관/개인 순매수(주수) 추이."""
    j = get_json(f"{API}/stock/{code}/trend?pageSize={size}")
    rows = j if isinstance(j, list) else j.get("trends", [])
    out = []
    for r in rows:
        out.append({
            "date": r.get("bizdate"),
            "close": num(r.get("closePrice")),
            "foreign_qty": num(r.get("foreignerPureBuyQuant")),
            "foreign_hold_pct": num(r.get("foreignerHoldRatio")),
            "organ_qty": num(r.get("organPureBuyQuant")),
            "individual_qty": num(r.get("individualPureBuyQuant")),
        })
    return out


def summarize_trend(trend):
    """수급 추이 요약: 5/20일 누적(억원 근사), 연속 순매수 일수."""
    def cum(days, key):
        v = 0.0
        for r in trend[:days]:
            q, c = r.get(key), r.get("close")
            if q is not None and c is not None:
                v += q * c
        return round(v / 1e8, 1)  # 억원

    def streak(key):
        n = 0
        for r in trend:
            q = r.get(key)
            if q is not None and q > 0:
                n += 1
            else:
                break
        return n

    return {
        "foreign_5d_100M": cum(5, "foreign_qty"),
        "foreign_20d_100M": cum(20, "foreign_qty"),
        "organ_5d_100M": cum(5, "organ_qty"),
        "organ_20d_100M": cum(20, "organ_qty"),
        "foreign_streak": streak("foreign_qty"),
        "organ_streak": streak("organ_qty"),
        "foreign_hold_pct": trend[0].get("foreign_hold_pct") if trend else None,
    }


# ---------------------------------------------------------------- 시세 랭킹
def get_market_rank(sort="marketValue", market="KOSPI", pages=2, page_size=100):
    """sort: marketValue | up | down. 종목 랭킹 목록."""
    out = []
    for page in range(1, pages + 1):
        j = get_json(f"{API}/stocks/{sort}/{market}?page={page}&pageSize={page_size}")
        stocks = j.get("stocks", [])
        if not stocks:
            break
        for s in stocks:
            if s.get("stockEndType") != "stock":
                continue
            out.append({
                "code": s["itemCode"],
                "name": s["stockName"],
                "close": num(s.get("closePrice")),
                "changeRate": num(s.get("fluctuationsRatio")),
                "tradingValue_M": num(s.get("accumulatedTradingValue")),
                "marketValue_100M": num(s.get("marketValue")),
            })
        if len(stocks) < page_size:
            break
    return out


# ---------------------------------------------------------------- 종목 상세
def get_stock_meta(code):
    """종목 메타: 업종코드(업종목록 no와 매핑), PER/PBR 등 지표, 목표주가 컨센서스."""
    j = get_json(f"{API}/stock/{code}/integration")
    infos = {i.get("code"): i.get("value") for i in (j.get("totalInfos") or [])}
    cons = j.get("consensusInfo") or {}
    return {
        "code": code,
        "name": j.get("stockName"),
        "industryCode": str(j.get("industryCode") or ""),
        "close": num(infos.get("closePrice")) or num(infos.get("lastClosePrice")),
        "per": num(infos.get("per")),
        "cns_per": num(infos.get("cnsPer")),      # 컨센서스 EPS 기준 포워드 PER
        "cns_eps": num(infos.get("cnsEps")),
        "pbr": num(infos.get("pbr")),
        "eps": num(infos.get("eps")),
        "high_52w": num(infos.get("highPriceOf52Weeks")),
        "dividendYield": num(infos.get("dividendYieldRatio")),
        "marketValue": infos.get("marketValue"),  # 원문 문자열 (조/억 표기)
        "target_price": num(cons.get("priceTargetMean")),
        "recomm_mean": num(cons.get("recommMean")),
    }


def get_finance_annual(code):
    """연간 재무 + 컨센서스(있으면). 매출액/영업이익/당기순이익/PER/PBR/ROE 행 추출.

    반환: {"periods": [...], "consensus_periods": [...], "rows": {지표: {기간: 값}}}
    """
    j = get_json(f"{API}/stock/{code}/finance/annual")
    fi = j.get("financeInfo") or {}
    titles = fi.get("trTitleList", [])
    periods = [t["key"] for t in titles]
    consensus = [t["key"] for t in titles if t.get("isConsensus") == "Y"]
    want = {"매출액", "영업이익", "당기순이익", "PER", "PBR", "ROE", "부채비율"}
    rows = {}
    for row in fi.get("rowList", []):
        title = row.get("title", "")
        base = title.split("(")[0].strip()
        if base not in want:
            continue
        vals = {}
        for k, cell in (row.get("columns") or {}).items():
            vals[k] = num(cell.get("value")) if isinstance(cell, dict) else num(cell)
        rows[base] = vals
    return {"periods": periods, "consensus_periods": consensus, "rows": rows}
