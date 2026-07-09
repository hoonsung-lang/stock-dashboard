# -*- coding: utf-8 -*-
"""한국 시장 수급/섹터 스캔 → output/kr_scan.json

사용: python scan_kr.py [--trend-top N]
  --trend-top N : 순매수 상위 몇 종목까지 20일 수급 추이를 딥다이브할지 (기본 25)
"""
import argparse
import sys
from collections import defaultdict

import kr_data as kr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trend-top", type=int, default=25)
    args = ap.parse_args()

    print("1/6 지수 ...", flush=True)
    indices = [kr.get_index("KOSPI"), kr.get_index("KOSDAQ")]

    print("2/6 업종 등락 ...", flush=True)
    industries = sorted(kr.get_industries(),
                        key=lambda g: g["changeRate"] or 0, reverse=True)

    print("3/6 테마 등락 ...", flush=True)
    themes = sorted(kr.get_themes(),
                    key=lambda g: g["changeRate"] or 0, reverse=True)

    print("4/6 외국인/기관 순매수 랭킹 ...", flush=True)
    deal = {
        "foreign_buy": kr.get_deal_rank("foreign", "buy"),
        "organ_buy": kr.get_deal_rank("organ", "buy"),
        "foreign_sell": kr.get_deal_rank("foreign", "sell"),
        "organ_sell": kr.get_deal_rank("organ", "sell"),
    }

    # 딥다이브 대상: 외국인+기관 순매수 상위 종목 합집합 (금액 기준)
    cand = {}
    for key in ("foreign_buy", "organ_buy"):
        for s in deal[key]:
            if s.get("is_etf"):
                continue  # 개별 종목 발굴이 목적이므로 ETF 제외
            c = cand.setdefault(s["code"], {"code": s["code"], "name": s["name"],
                                            "buy_amount_M": 0})
            c["buy_amount_M"] += s["amount_M"] or 0
    top = sorted(cand.values(), key=lambda x: x["buy_amount_M"], reverse=True)
    top = top[:args.trend_top]

    ind_name = {str(g["no"]): g["name"] for g in industries}

    print(f"5/6 상위 {len(top)}종목 20일 수급 딥다이브 ...", flush=True)
    focus = []
    for i, s in enumerate(top):
        try:
            meta = kr.get_stock_meta(s["code"])
            trend = kr.get_investor_trend(s["code"], size=20)
            close, tgt = meta.get("close"), meta.get("target_price")
            h52 = meta.get("high_52w")
            focus.append({
                **s,
                "industry": ind_name.get(meta.get("industryCode"), "기타"),
                "close": close,
                "per": meta.get("per"),
                "cns_per": meta.get("cns_per"),
                "pbr": meta.get("pbr"),
                "target_price": tgt,
                "upside_pct": round((tgt / close - 1) * 100, 1) if tgt and close else None,
                "off_52w_high_pct": round((close / h52 - 1) * 100, 1) if h52 and close else None,
                **kr.summarize_trend(trend),
            })
        except Exception as e:  # noqa: BLE001
            print(f"  skip {s['code']} {s['name']}: {e}", file=sys.stderr)
        if (i + 1) % 10 == 0:
            print(f"  ... {i + 1}/{len(top)}", flush=True)

    # 업종별 수급 집계 (딥다이브 종목 기준, 20일 누적 억원)
    sector_flow = defaultdict(lambda: {"foreign_20d_100M": 0.0, "organ_20d_100M": 0.0,
                                       "stocks": []})
    for f in focus:
        ind = f.get("industry") or "기타"
        sector_flow[ind]["foreign_20d_100M"] += f.get("foreign_20d_100M") or 0
        sector_flow[ind]["organ_20d_100M"] += f.get("organ_20d_100M") or 0
        sector_flow[ind]["stocks"].append(f["name"])
    sector_flow = [{"industry": k, **v} for k, v in sector_flow.items()]
    sector_flow.sort(key=lambda x: x["foreign_20d_100M"] + x["organ_20d_100M"],
                     reverse=True)

    print("6/6 거래대금 상위 ...", flush=True)
    mv = kr.get_market_rank("marketValue", "KOSPI", pages=1) + \
         kr.get_market_rank("marketValue", "KOSDAQ", pages=1)
    trading_top = sorted(mv, key=lambda s: s["tradingValue_M"] or 0,
                         reverse=True)[:20]

    from common import save_json
    save_json("kr_scan", {
        "indices": indices,
        "industries_top": industries[:15],
        "industries_bottom": industries[-10:],
        "themes_top": themes[:20],
        "deal_rank": {k: v[:20] for k, v in deal.items()},
        "focus_stocks": focus,          # 수급 딥다이브 (연속매수일·5/20일 누적 억원)
        "sector_flow": sector_flow,     # 업종별 외인/기관 20일 순매수 집계
        "trading_value_top": trading_top,
    })


if __name__ == "__main__":
    main()
