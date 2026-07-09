# -*- coding: utf-8 -*-
"""클라우드 스캔 결과를 scout/data/ 에 발행 (매니페스트 merge).

GitHub Actions(scout-scan.yml)에서 스캔 스크립트 실행 후 호출한다.
스캔 JSON(kr_scan/us_scan/kr_screen/us_screen)만 갱신하고, insights·성적표·
리포트 등 Claude(로컬)가 소유하는 항목은 건드리지 않는다 — manifest 를 읽어
자기 키만 덮어쓰는 merge 방식이라 두 발행자가 같은 리포에 충돌 없이 쓴다.

사용: python -X utf8 publish_scan.py [--only kr_scan us_scan ...]
  (기본: engine/output 에 존재하는 스캔 JSON 전부)
"""
import argparse
import json
import os
import shutil
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))          # scout/engine
OUTPUT = os.path.join(HERE, "output")                       # 스캔 산출물
DATA = os.path.normpath(os.path.join(HERE, "..", "data"))   # scout/data (발행 대상)

SCAN_FILES = ["kr_scan", "us_scan", "kr_screen", "us_screen"]


def _generated_of(path):
    """JSON 의 _generated 필드(common.save_json 이 심음) 우선, 없으면 mtime."""
    try:
        with open(path, encoding="utf-8") as f:
            g = json.load(f).get("_generated")
        if g:
            return g[:16]  # 'YYYY-MM-DD HH:MM'
    except Exception:
        pass
    return datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None,
                    help="발행할 스캔 이름 (기본: output 에 있는 것 전부)")
    args = ap.parse_args()

    os.makedirs(DATA, exist_ok=True)
    names = args.only or SCAN_FILES

    # 기존 manifest 읽어 merge (없으면 새로)
    mpath = os.path.join(DATA, "manifest.json")
    manifest = {}
    if os.path.exists(mpath):
        try:
            with open(mpath, encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            manifest = {}
    manifest.setdefault("files", {})
    manifest.setdefault("reports", [])

    published = []
    for name in names:
        src = os.path.join(OUTPUT, name + ".json")
        if not os.path.exists(src):
            print(f"[skip] {name}.json 없음 (스캔 미실행/실패)")
            continue
        shutil.copy2(src, os.path.join(DATA, name + ".json"))
        manifest["files"][name] = _generated_of(src)
        published.append(name)

    if not published:
        print("[publish_scan] 발행할 스캔 없음")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    manifest["scan_published"] = now
    manifest["published"] = now  # 하위호환(전체 최신 표기)

    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    print(f"[publish_scan] 발행: {', '.join(published)} → {DATA}")


if __name__ == "__main__":
    main()
