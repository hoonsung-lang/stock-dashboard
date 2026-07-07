# -*- coding: utf-8 -*-
"""
data/data.json 의 git 커밋 히스토리에서 종목별 현재가(p_cur) 시계열을 추출해
data/history.json 을 생성한다. 새 수집 없이 과거 커밋만으로 스파크라인 데이터를 만든다.

출력: data/history.json
  {
    "generated_at": ISO8601,
    "dates": ["2026-06-23", ..., "2026-07-06"],   # 커밋 날짜(오름차순)
    "series": {                                     # "시장:티커" → 종가 배열
      "US:AAPL": [270.51, ..., 308.63],            # dates 와 같은 길이, 누락은 null
      ...
    }
  }

- 최근 MAX_COMMITS 개 커밋만 사용(스파크라인은 단기 추세면 충분, 파일 비대화 방지).
- 하루에 여러 번 커밋된 날은 마지막(최신) 커밋만 사용해 날짜당 1점 유지.
- 종목은 최신 커밋 기준 유니버스로 한정(상장폐지·유니버스 이탈 종목은 제외).
"""
import json
import subprocess
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "data.json"
OUT = ROOT / "data" / "history.json"
REL = "data/data.json"           # git 경로(리포 루트 기준)
MAX_COMMITS = 60                 # 스파크라인에 쓸 최근 커밋 수 상한


def git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    ).stdout


def key(row):
    return f"{row.get('market')}:{row.get('ticker')}"


def main():
    # 1) data/data.json 을 건드린 커밋들을 (해시, 날짜) 오래된→최신 순으로
    log = git("log", "--reverse", "--date=short",
              "--format=%H\t%ad", "--", REL).strip()
    if not log:
        print("data/data.json 커밋 히스토리가 없습니다 — 종료.")
        return
    commits = [line.split("\t") for line in log.splitlines() if "\t" in line]

    # 날짜당 마지막(최신) 커밋만 남겨 하루 1점 보장
    by_date = {}
    for h, d in commits:
        by_date[d] = h                       # 같은 날짜면 뒤(더 최신) 커밋으로 덮어씀
    dates = sorted(by_date)[-MAX_COMMITS:]   # 최근 N일

    # 2) 각 커밋 시점의 data.json 에서 종목별 p_cur 추출
    snapshots = {}                           # date → {key: p_cur}
    for d in dates:
        raw = git("show", f"{by_date[d]}:{REL}")
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        snapshots[d] = {key(s): s.get("p_cur") for s in payload.get("stocks", [])}
    dates = [d for d in dates if d in snapshots]

    # 3) 유니버스 = 최신 data.json 기준. 종목별로 날짜순 가격 배열 구성
    latest = json.loads(DATA.read_text(encoding="utf-8"))
    series = {}
    for s in latest.get("stocks", []):
        k = key(s)
        vals = [snapshots[d].get(k) for d in dates]
        # 유효 포인트가 2개 미만이면 스파크라인이 무의미 → 제외
        if sum(v is not None for v in vals) >= 2:
            series[k] = vals

    payload = {
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "dates": dates,
        "series": series,
    }
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"history.json 생성: {len(dates)}일 × {len(series)}종목 → {OUT}")


if __name__ == "__main__":
    main()
