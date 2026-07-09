# -*- coding: utf-8 -*-
"""stock-scout 공용 유틸리티: HTTP 세션, JSON 저장, 경로."""
import json
import os
import time
from datetime import datetime

import requests

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(SKILL_ROOT, "output")
DATA_DIR = os.path.join(SKILL_ROOT, "data")  # 유니버스 캐시 등
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

_session = None


def session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": UA})
    return _session


def get_json(url, retries=3, delay=0.15, timeout=15):
    """네이버 API 등에서 JSON GET. 재시도 + 요청 간 딜레이."""
    last_err = None
    for i in range(retries):
        try:
            r = session().get(url, timeout=timeout)
            r.raise_for_status()
            time.sleep(delay)
            return r.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1.0 * (i + 1))
    raise RuntimeError(f"GET 실패 {url}: {last_err}")


def get_text(url, encoding=None, timeout=15):
    r = session().get(url, timeout=timeout)
    r.raise_for_status()
    if encoding:
        r.encoding = encoding
    return r.text


def num(s):
    """'1,234' / '+1,234' / '46.69%' / '25.70배' / '12,372원' → float 또는 None.

    주의: '13조 6,984억' 같은 조/억 복합 표기는 첫 숫자만 잡히므로 사용하지 말 것.
    """
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).replace(",", "").replace("+", "").strip()
    if s in ("", "-", "N/A", "nan"):
        return None
    import re
    m = re.match(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def save_json(name, payload):
    """output/{name}.json 저장. 생성 시각 메타 포함."""
    payload = {"_generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **payload}
    path = os.path.join(OUTPUT_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1, default=str)
    print(f"[saved] {path}")
    return path


def load_json(name):
    path = os.path.join(OUTPUT_DIR, f"{name}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)
