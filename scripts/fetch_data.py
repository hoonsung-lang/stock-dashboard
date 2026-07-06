# -*- coding: utf-8 -*-
"""
미국/한국/일본 주가 대시보드용 데이터 수집기.

기준 시점(국가별 실제 거래일):
  - open    : 해당 연도 첫 거래일
  - m2/m4/… : 지나간 짝수달의 마지막 거래일 (config.checkpoints 가 자동 생성)
  - current : 최근 거래일

연도는 실행 시점 기준 자동. 연초에 그 해 거래 데이터가 아직 없으면 전년도로 폴백.
상승률(%) = (해당 시점가 / 개장일가 - 1) * 100

출력: data/data.json
  {
    "generated_at": ISO8601,
    "year": 2026,
    "checkpoints": ["m2", "m4", "m6", ...],        # 표시 순서
    "labels": {"open": "...", "m2": "...", ..., "current": "..."},
    "dates":  {"US": {...}, "KR": {...}, "JP": {...}},
    "failed_markets": [],                           # 수집 실패한 시장
    "stocks": [ {ticker, name, market, p_open, p_m2, ..., p_cur,
                 r_m2, ..., r_cur}, ... ]
  }

미국/일본은 yfinance, 한국은 FinanceDataReader 사용.
한 시장이 실패해도 나머지는 정상 수집되도록 try/except 로 격리하되,
실패 시장은 failed_markets 로 기록해 프런트에서 경고를 띄운다.
전 시장 실패(종목 0개)면 파일을 쓰지 않고 종료코드 1 → Actions 가 실패로 감지.
"""
import os
import sys
import json
import datetime as dt
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "data.json"

TODAY = dt.date.today()


def round2(x):
    return None if x is None else round(float(x), 2)


def pct(cur, base):
    if cur is None or base is None or base == 0:
        return None
    return round((cur / base - 1.0) * 100.0, 2)


# ---------------------------------------------------------------------------
# 미국 / 일본 (yfinance)
# ---------------------------------------------------------------------------
def fetch_yf(market, name_map, year, cps, suffix=""):
    import yfinance as yf

    tickers = [t + suffix for t in name_map.keys()]
    print(f"[{market}] {len(tickers)} 종목 다운로드 중...", flush=True)

    df = yf.download(
        tickers, start=f"{year}-01-01",
        end=(TODAY + dt.timedelta(days=1)).isoformat(),
        auto_adjust=True, progress=False, group_by="ticker", threads=True,
    )

    # 거래일 집합으로 기준일 결정
    all_dates = sorted(set(df.index.date))
    if not all_dates:
        raise RuntimeError("거래일 데이터 없음")

    def resolve(cutoff):
        y, m, d = cutoff
        c = dt.date(y, m, d)
        elig = [x for x in all_dates if x <= c]
        return elig[-1] if elig else None

    dates = {"open": all_dates[0]}
    dates.update({k: resolve(v) for k, v in cps.items()})
    dates["current"] = all_dates[-1]

    def price_at(s, target):
        if target is None:
            return None
        sub = s[s.index.date <= target].dropna()
        return float(sub.iloc[-1]) if len(sub) else None

    rows = []
    for code, nm in name_map.items():
        tk = code + suffix
        try:
            s = df[tk]["Close"].dropna() if len(tickers) > 1 else df["Close"].dropna()
        except Exception:
            continue
        if s.empty:
            continue
        p_open = price_at(s, dates["open"])
        p_cur = price_at(s, dates["current"])
        if p_open is None or p_cur is None:
            continue
        row = {"ticker": code, "name": nm, "market": market,
               "p_open": round2(p_open), "p_cur": round2(p_cur),
               "r_cur": pct(p_cur, p_open)}
        for k in cps:
            p = price_at(s, dates[k])
            row["p_" + k] = round2(p)
            row["r_" + k] = pct(p, p_open)
        rows.append(row)
    print(f"[{market}] {len(rows)} 종목 수집 완료", flush=True)
    return rows, {k: (v.isoformat() if v else None) for k, v in dates.items()}


# ---------------------------------------------------------------------------
# 한국 (FinanceDataReader — KOSPI/KOSDAQ 시총 상위 주요종목, 병렬 수집)
#   * pykrx 의 KRX 직접 엔드포인트는 해외/클라우드 IP에서 차단되는 경우가 많아
#     네이버 기반 FDR 로 일원화한다.
# ---------------------------------------------------------------------------
def fetch_kr(year, cps, max_workers=12):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import FinanceDataReader as fdr

    # 거래일 달력: KOSPI 지수(KS11) 시계열에서 추출
    ks = fdr.DataReader("KS11", f"{year}-01-01")
    trading_days = sorted(d.date() for d in ks.index)
    if not trading_days:
        raise RuntimeError("거래일 달력 수집 실패")

    def resolve(cutoff):
        y, m, d = cutoff
        c = dt.date(y, m, d)
        elig = [x for x in trading_days if x <= c]
        return elig[-1] if elig else trading_days[0]

    targets = {"open": trading_days[0]}
    targets.update({k: resolve(v) for k, v in cps.items()})
    targets["current"] = trading_days[-1]
    date_keys = {k: v.isoformat() for k, v in targets.items()}
    print(f"[KR] 기준일 {date_keys}", flush=True)

    # 종목 목록 → 시가총액 상위 주요종목 큐레이션 (KOSPI N + KOSDAQ M)
    listing = fdr.StockListing("KRX")
    code_col = "Code" if "Code" in listing.columns else listing.columns[0]
    cap_col = "Marcap" if "Marcap" in listing.columns else None

    def pick_top(market_key, topn):
        rows = []
        for _, r in listing.iterrows():
            mk = str(r.get("Market", "")).upper()
            if market_key not in mk:
                continue
            name = str(r.get("Name", ""))
            # 우선주(이름이 '우'/'우B' 등으로 끝남) 제외 → 보통주 위주
            if name.endswith("우") or name.endswith("우B") or name.endswith("(전환)"):
                continue
            code = str(r[code_col]).zfill(6)
            cap = float(r.get(cap_col) or 0) if cap_col else 0
            rows.append((cap, code, name,
                         "KOSDAQ" if "KOSDAQ" in mk else "KOSPI"))
        rows.sort(key=lambda x: x[0], reverse=True)
        return [(c, n, s) for _, c, n, s in rows[:topn]]

    universe = pick_top("KOSPI", config.KR_TOP_KOSPI) + \
        pick_top("KOSDAQ", config.KR_TOP_KOSDAQ)
    print(f"[KR] 시총 상위 {len(universe)} 종목 시세 수집 시작...", flush=True)

    def price_at(s, target):
        sub = s[s.index.date <= target].dropna()
        return float(sub.iloc[-1]) if len(sub) else None

    def fetch_one(item):
        code, name, sub = item
        try:
            df = fdr.DataReader(code, f"{year}-01-01")
        except Exception:
            return None
        if df is None or df.empty or "Close" not in df.columns:
            return None
        s = df["Close"].dropna()
        if s.empty:
            return None
        p_open = price_at(s, targets["open"])
        p_cur = price_at(s, targets["current"])
        if not p_open or not p_cur:
            return None
        row = {"ticker": code, "name": name, "market": "KR", "submarket": sub,
               "p_open": round2(p_open), "p_cur": round2(p_cur),
               "r_cur": pct(p_cur, p_open)}
        for k in cps:
            p = price_at(s, targets[k])
            row["p_" + k] = round2(p)
            row["r_" + k] = pct(p, p_open)
        return row

    rows = []
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(fetch_one, it) for it in universe]
        for f in as_completed(futs):
            done += 1
            if done % 300 == 0:
                print(f"[KR] 진행 {done}/{len(universe)} (유효 {len(rows)})", flush=True)
            r = f.result()
            if r:
                rows.append(r)
    print(f"[KR] {len(rows)} 종목 수집 완료", flush=True)
    return rows, date_keys


# ---------------------------------------------------------------------------
def collect(year):
    """해당 연도 기준으로 3개 시장 수집. (stocks, dates, failed, cps) 반환."""
    cps = config.checkpoints(year, TODAY)
    print(f"기준 연도 {year} · 체크포인트 {list(cps)}", flush=True)
    stocks, dates, failed = [], {}, []

    jobs = [("US", lambda: fetch_yf("US", config.US_STOCKS, year, cps)),
            ("JP", lambda: fetch_yf("JP", config.JP_STOCKS, year, cps, suffix=".T")),
            ("KR", lambda: fetch_kr(year, cps))]
    for market, job in jobs:
        try:
            rows, d = job()
            stocks += rows
            dates[market] = d
        except Exception as e:
            print(f"[{market}] 실패: {e}", flush=True)
            failed.append(market)
    return stocks, dates, failed, cps


def main():
    year = TODAY.year
    stocks, dates, failed, cps = collect(year)

    # 연초: 그 해 거래 데이터가 아직 없으면 전년도 최종 성적으로 폴백
    if not stocks and TODAY.month == 1:
        print(f"\n{year}년 데이터 없음 → {year - 1}년으로 폴백", flush=True)
        year -= 1
        stocks, dates, failed, cps = collect(year)

    if not stocks:
        print("\n전 시장 수집 실패 — data.json 을 갱신하지 않고 종료합니다.",
              file=sys.stderr, flush=True)
        sys.exit(1)

    # 라벨(대표 시장 기준 표기용)
    ref = dates.get("US") or dates.get("KR") or dates.get("JP") or {}
    payload = {
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "year": year,
        "checkpoints": list(cps),
        "labels": ref,
        "dates": dates,
        "failed_markets": failed,
        "count": len(stocks),
        "stocks": stocks,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"\n총 {len(stocks)} 종목 → {OUT}", flush=True)
    if failed:
        print(f"⚠️ 수집 실패 시장: {', '.join(failed)}", flush=True)


if __name__ == "__main__":
    main()
