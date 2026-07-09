# -*- coding: utf-8 -*-
"""성장주 스크리닝 → output/kr_screen.json / us_screen.json

한국: 시총 상위 유니버스 전수 조사 — 컨센서스 영업이익 성장률 + 포워드 PER 기반.
미국: Yahoo 서버사이드 스크리너(성장주 프리셋) + 펀더멘털 필터.

사용:
  python screen_growth.py --market kr [--kospi 150] [--kosdaq 50]
                          [--min-growth 15] [--max-per 30]
  python screen_growth.py --market us [--min-growth 15]
  python screen_growth.py --market all
"""
import argparse
import sys

from common import save_json


# ---------------------------------------------------------------- KR
def growth_metrics(fin):
    """finance_annual 결과에서 성장률/포워드 지표 계산."""
    rows, cons = fin["rows"], fin["consensus_periods"]
    actual = [p for p in fin["periods"] if p not in cons]
    if not actual or not cons:
        return None
    a, c = actual[-1], cons[0]

    def g(metric):
        va, vc = (rows.get(metric) or {}).get(a), (rows.get(metric) or {}).get(c)
        if va is None or vc is None or va <= 0:
            return None
        return round((vc / va - 1) * 100, 1)

    op_a = (rows.get("영업이익") or {}).get(a)
    op_c = (rows.get("영업이익") or {}).get(c)
    return {
        "actual_period": a, "consensus_period": c,
        "rev_growth_pct": g("매출액"),
        "op_growth_pct": g("영업이익"),
        "np_growth_pct": g("당기순이익"),
        "turnaround": bool(op_a is not None and op_c is not None
                           and op_a <= 0 < op_c),
        "fwd_per": (rows.get("PER") or {}).get(c),
        "fwd_roe": (rows.get("ROE") or {}).get(c),
    }


def screen_kr(kospi_n, kosdaq_n, min_growth, max_per, finalists=30):
    import kr_data as kr

    print(f"[KR] 유니버스 수집: KOSPI {kospi_n} + KOSDAQ {kosdaq_n} ...", flush=True)
    uni = (kr.get_market_rank("marketValue", "KOSPI",
                              pages=(kospi_n + 99) // 100)[:kospi_n]
           + kr.get_market_rank("marketValue", "KOSDAQ",
                                pages=(kosdaq_n + 99) // 100)[:kosdaq_n])
    uni = [s for s in uni if not kr.is_etf_like(s["name"])]

    print(f"[KR] {len(uni)}종목 재무/컨센서스 조회 (수 분 소요) ...", flush=True)
    rows = []
    for i, s in enumerate(uni):
        try:
            m = growth_metrics(kr.get_finance_annual(s["code"]))
            if m:
                rows.append({**s, **m})
        except Exception:  # noqa: BLE001
            pass
        if (i + 1) % 50 == 0:
            print(f"  ... {i + 1}/{len(uni)}", flush=True)

    # 필터: 컨센서스 영업이익 성장 or 흑자전환 + 포워드 PER 상한
    cand = []
    for r in rows:
        og = r.get("op_growth_pct")
        if not (r["turnaround"] or (og is not None and og >= min_growth)):
            continue
        fp = r.get("fwd_per")
        if fp is None or fp <= 0 or fp > max_per:
            continue
        r["peg_like"] = round(fp / og, 2) if og and og > 0 else None
        cand.append(r)
    cand.sort(key=lambda r: (r["peg_like"] is None, r["peg_like"]))
    cand = cand[:finalists]

    print(f"[KR] 후보 {len(cand)}종목 목표주가 컨센서스 조회 ...", flush=True)
    for r in cand:
        try:
            meta = kr.get_stock_meta(r["code"])
            tgt, close = meta.get("target_price"), r.get("close")
            r["target_price"] = tgt
            r["upside_pct"] = (round((tgt / close - 1) * 100, 1)
                               if tgt and close else None)
            r["off_52w_high_pct"] = (round((close / meta["high_52w"] - 1) * 100, 1)
                                     if meta.get("high_52w") and close else None)
        except Exception:  # noqa: BLE001
            pass

    save_json("kr_screen", {
        "criteria": {"min_op_growth_pct": min_growth, "max_fwd_per": max_per,
                     "universe": f"KOSPI{kospi_n}+KOSDAQ{kosdaq_n}"},
        "screened_total": len(rows),
        "candidates": cand,
    })


# ---------------------------------------------------------------- US
US_PRESETS = ["growth_technology_stocks", "undervalued_growth_stocks",
              "small_cap_gainers"]


def screen_us(min_growth):
    import yfinance as yf

    import us_data as us

    tickers = []
    for preset in US_PRESETS:
        try:
            r = yf.screen(preset, count=25)
            got = [q["symbol"] for q in r.get("quotes", []) if q.get("symbol")]
            print(f"[US] {preset}: {len(got)}종목", flush=True)
            tickers += got
        except Exception as e:  # noqa: BLE001
            print(f"[US] {preset} 실패: {e}", file=sys.stderr)
    tickers = list(dict.fromkeys(tickers))

    print(f"[US] {len(tickers)}종목 펀더멘털 조회 ...", flush=True)
    rows = us.get_fundamentals(tickers)

    cand = []
    for r in rows:
        eg, rg = r.get("earningsGrowth_pct"), r.get("revenueGrowth_pct")
        if not ((eg is not None and eg >= min_growth)
                or (rg is not None and rg >= min_growth)):
            continue
        fp = r.get("forwardPE")
        if fp is None or fp <= 0:
            continue
        r["peg_like"] = round(fp / eg, 2) if eg and eg > 0 else None
        tp, cp = r.get("targetMeanPrice"), r.get("currentPrice")
        r["upside_pct"] = round((tp / cp - 1) * 100, 1) if tp and cp else None
        cand.append(r)
    cand.sort(key=lambda r: (r["peg_like"] is None, r["peg_like"]))

    save_json("us_screen", {
        "criteria": {"min_growth_pct": min_growth, "presets": US_PRESETS},
        "screened_total": len(rows),
        "candidates": cand,
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["kr", "us", "all"], default="all")
    ap.add_argument("--kospi", type=int, default=150)
    ap.add_argument("--kosdaq", type=int, default=50)
    ap.add_argument("--min-growth", type=float, default=15)
    ap.add_argument("--max-per", type=float, default=30)
    args = ap.parse_args()

    if args.market in ("kr", "all"):
        screen_kr(args.kospi, args.kosdaq, args.min_growth, args.max_per)
    if args.market in ("us", "all"):
        screen_us(args.min_growth)


if __name__ == "__main__":
    main()
