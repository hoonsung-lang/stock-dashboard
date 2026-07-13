# -*- coding: utf-8 -*-
"""미국 시장 데이터 수집기 — yfinance 기반."""
import os

import pandas as pd
import yfinance as yf

from common import DATA_DIR

# 벤치마크 + 11개 SPDR 섹터 + 테마 ETF
SECTOR_ETFS = {
    "SPY": "S&P500(벤치마크)",
    "QQQ": "나스닥100",
    "IWM": "러셀2000(중소형)",
    "XLK": "기술",
    "XLC": "커뮤니케이션",
    "XLY": "임의소비재",
    "XLP": "필수소비재",
    "XLV": "헬스케어",
    "XLF": "금융",
    "XLI": "산업재",
    "XLE": "에너지",
    "XLB": "소재",
    "XLU": "유틸리티",
    "XLRE": "리츠",
    "SMH": "반도체",
    "IGV": "소프트웨어",
    "XBI": "바이오텍",
    "ITA": "방산/우주",
    "URA": "우라늄",
    "NLR": "원자력",
    "ICLN": "클린에너지",
    "PAVE": "인프라",
    "XHB": "주택건설",
    "KRE": "지방은행",
    "GDX": "금광",
}


def _drop_intraday(df):
    """미완성 장중 봉 제거 → 항상 마지막 '정규 종가' 기준.

    yfinance 일봉은 장중에 돌리면 당일(ET) 봉이 미완성 상태로 들어온다.
    스캔 시점 ET가 정규장 마감(16:00) 전이고 마지막 봉 날짜가 오늘이면 그
    봉을 버린다. 자동 실행(18:20 ET)은 마감 후라 영향 없음.
    """
    if len(df.index) == 0:
        return df
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        et = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return df  # tz 정보 없으면 원본 유지(자동 실행은 마감 후라 안전)
    last_date = str(df.index[-1].date() if hasattr(df.index[-1], "date")
                    else df.index[-1])[:10]
    if last_date == et.strftime("%Y-%m-%d") and et.hour < 16:
        return df.iloc[:-1]
    return df


def download_prices(tickers, period="1y"):
    """종가 DataFrame(index=date, columns=ticker)과 거래량 DataFrame.

    장중 미완성 봉은 제외해 항상 마지막 정규 종가를 반환한다.
    """
    raw = yf.download(list(tickers), period=period, progress=False,
                      auto_adjust=True, group_by="column", threads=True)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    vol = raw["Volume"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Volume"]]
    close = _drop_intraday(close.dropna(how="all"))
    vol = vol.reindex(close.index)
    return close, vol


def perf_table(close, vol=None, benchmark="SPY"):
    """수익률/상대강도/52주고가 대비/거래량 추세 테이블 생성."""
    def ret(days):
        if len(close) <= days:
            return pd.Series(dtype=float)
        return (close.iloc[-1] / close.iloc[-1 - days] - 1) * 100

    r = pd.DataFrame({
        "ret_1d": ret(1),
        "ret_1w": ret(5), "ret_1m": ret(21), "ret_3m": ret(63), "ret_6m": ret(126),
    })
    r["close"] = close.iloc[-1]  # 최근 종가(레벨) — 카드 표시용
    r["off_52w_high_pct"] = (close.iloc[-1] / close.max() - 1) * 100
    if benchmark in r.index:
        for c in ("ret_1w", "ret_1m", "ret_3m", "ret_6m"):
            r["rs_" + c[4:]] = r[c] - r.loc[benchmark, c]
    if vol is not None and len(vol) >= 60:
        v20 = vol.iloc[-20:].mean()
        v60 = vol.iloc[-60:].mean()
        r["vol_ratio_20_60"] = (v20 / v60).round(2)  # >1 이면 최근 거래 증가
    return r.round(2)


def get_universe(refresh=False):
    """S&P500 + 나스닥100 티커 목록 (위키피디아, data/에 캐시)."""
    cache = os.path.join(DATA_DIR, "universe_us.csv")
    if os.path.exists(cache) and not refresh:
        return pd.read_csv(cache)
    from io import StringIO

    from common import get_text

    def read_tables(url):
        return pd.read_html(StringIO(get_text(url)))

    frames = []
    sp = read_tables("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
    frames.append(pd.DataFrame({
        "ticker": sp["Symbol"], "name": sp["Security"], "sector": sp["GICS Sector"],
        "industry": sp["GICS Sub-Industry"], "index": "SP500"}))
    nd = None
    for t in read_tables("https://en.wikipedia.org/wiki/Nasdaq-100"):
        if "Ticker" in t.columns or "Symbol" in t.columns:
            col = "Ticker" if "Ticker" in t.columns else "Symbol"
            if len(t) > 80:
                nd = t.rename(columns={col: "Symbol"})
                break
    if nd is not None:
        name_col = "Company" if "Company" in nd.columns else nd.columns[0]
        sec_col = "GICS Sector" if "GICS Sector" in nd.columns else None
        frames.append(pd.DataFrame({
            "ticker": nd["Symbol"], "name": nd[name_col],
            "sector": nd[sec_col] if sec_col else "",
            "industry": "", "index": "NDX"}))
    uni = pd.concat(frames).drop_duplicates("ticker").reset_index(drop=True)
    uni["ticker"] = uni["ticker"].str.replace(".", "-", regex=False)
    uni.to_csv(cache, index=False)
    return uni


def get_fundamentals(tickers):
    """yfinance .info에서 성장/밸류에이션 핵심 필드 추출 (건당 ~1초, 수십 개 권장)."""
    out = []
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            out.append({
                "ticker": t,
                "name": info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "marketCap_B": round((info.get("marketCap") or 0) / 1e9, 1),
                "forwardPE": info.get("forwardPE"),
                "trailingPE": info.get("trailingPE"),
                "pegRatio": info.get("trailingPegRatio") or info.get("pegRatio"),
                "revenueGrowth_pct": _pct(info.get("revenueGrowth")),
                "earningsGrowth_pct": _pct(info.get("earningsGrowth")),
                "targetMeanPrice": info.get("targetMeanPrice"),
                "currentPrice": info.get("currentPrice"),
                "recommendationMean": info.get("recommendationMean"),
                "off_52w_high_pct": _off_high(info),
            })
        except Exception as e:  # noqa: BLE001
            print(f"  info 실패 {t}: {e}")
    return out


def _pct(x):
    return round(x * 100, 1) if isinstance(x, (int, float)) else None


def _off_high(info):
    p, h = info.get("currentPrice"), info.get("fiftyTwoWeekHigh")
    if p and h:
        return round((p / h - 1) * 100, 1)
    return None
