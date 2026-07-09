# -*- coding: utf-8 -*-
"""미국 시장 섹터 상대강도 + 모멘텀 스캔 → output/us_scan.json

사용: python scan_us.py [--deep-top N] [--refresh-universe]
  --deep-top N : 모멘텀 상위 몇 종목의 펀더멘털(.info)까지 조회할지 (기본 30)
"""
import argparse

import pandas as pd

import us_data as us
from common import save_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deep-top", type=int, default=30)
    ap.add_argument("--refresh-universe", action="store_true")
    args = ap.parse_args()

    print("1/4 섹터/테마 ETF 상대강도 ...", flush=True)
    close, vol = us.download_prices(us.SECTOR_ETFS.keys(), period="1y")
    etf = us.perf_table(close, vol)
    etf["label"] = pd.Series(us.SECTOR_ETFS)
    etf = etf.sort_values("rs_3m", ascending=False)
    sectors = etf.reset_index(names="ticker").to_dict("records")

    print("2/4 유니버스 로드 (S&P500+NDX) ...", flush=True)
    uni = us.get_universe(refresh=args.refresh_universe)
    meta = uni.set_index("ticker")[["name", "sector", "industry"]]

    print(f"3/4 {len(uni)}종목 1년 가격 다운로드 & 모멘텀 랭킹 ...", flush=True)
    uclose, uvol = us.download_prices(uni["ticker"].tolist(), period="1y")
    perf = us.perf_table(uclose, uvol, benchmark=None)
    perf = perf.dropna(subset=["ret_3m"])
    # 모멘텀 점수: 3개월 60% + 1개월 40%, 단 52주 고가 대비 -25% 이상 이탈은 제외
    perf["momentum"] = perf["ret_3m"] * 0.6 + perf["ret_1m"] * 0.4
    strong = perf[perf["off_52w_high_pct"] > -25].sort_values("momentum",
                                                              ascending=False)
    top = strong.head(args.deep_top)
    momentum_list = (top.join(meta).reset_index(names="ticker")
                     .to_dict("records"))

    print(f"4/4 모멘텀 상위 {len(top)}종목 펀더멘털 조회 ...", flush=True)
    fundamentals = us.get_fundamentals(top.index.tolist())
    fmap = {f["ticker"]: f for f in fundamentals}
    for row in momentum_list:
        f = fmap.get(row["ticker"], {})
        row.update({k: f.get(k) for k in
                    ("marketCap_B", "forwardPE", "pegRatio", "revenueGrowth_pct",
                     "earningsGrowth_pct", "targetMeanPrice", "currentPrice",
                     "recommendationMean")})
        tp, cp = row.get("targetMeanPrice"), row.get("currentPrice")
        row["upside_pct"] = round((tp / cp - 1) * 100, 1) if tp and cp else None

    # 섹터별 모멘텀 상위 분포 (어느 섹터에 강한 종목이 몰리는지)
    sector_count = {}
    for row in momentum_list:
        s = row.get("sector") or "N/A"
        sector_count[s] = sector_count.get(s, 0) + 1

    save_json("us_scan", {
        "sector_etfs": sectors,
        "momentum_top": momentum_list,
        "momentum_sector_distribution": sorted(
            sector_count.items(), key=lambda x: -x[1]),
    })


if __name__ == "__main__":
    main()
