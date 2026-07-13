# scout/engine — 클라우드 스캔 엔진 (미러)

`scout-scan.yml` GitHub Actions 워크플로가 매 평일 아침 시장 스캔을 실행하는 코드다.
PC가 꺼져 있어도 시장 데이터(외국인/기관 수급·섹터 RS·모멘텀·성장주 스크리닝)는
클라우드에서 자동 갱신된다.

공개 페이지: https://hoonsung-lang.github.io/stock-dashboard/scout/

## 자동 업데이트 일정 (공개 페이지 기준)

`scout/data/`(공개 페이지가 읽는 데이터)를 갱신하는 워크플로는 `scout-scan.yml`
**하나뿐**이다. (루트 대시보드를 갱신하는 `update-data.yml`은 scout와 무관하다.)

```
cron: "20 22 * * 0-4"    # 22:20 UTC, UTC 요일 일~목
```

**중요: GitHub Actions cron은 UTC 요일로 평가된다.** KST(UTC+9)로 변환하면 날짜가
하루 밀려, 결과적으로 **KST 월~금 아침 07:20 예약**이 된다.

| UTC 예약 | → KST 착지 |
|---|---|
| 일 22:20 | 월 07:20 |
| 월 22:20 | 화 07:20 |
| 화 22:20 | 수 07:20 |
| 수 22:20 | 목 07:20 |
| 목 22:20 | 금 07:20 |

- **한국수급·미국섹터 스캔**(kr_scan·us_scan): KST 평일(월~금) 매일 아침 갱신.
- **성장주 스크리닝**(kr_screen·us_screen): **주 1회만** — UTC 월요일(=KST 화요일 아침)에만
  실행하고, 다른 요일엔 기존 스크리닝 JSON을 그대로 유지한다(파일이 없으면 예외적으로 실행).

### 데이터 기준 시점 (왜 07:20인가)
22:20 UTC = **18:20 ET / 07:20 KST** — 미·한 종가를 모두 담기 좋은 시점이다.
- **미국**: 16:00 ET 마감 2시간 뒤라 당일 **정규 종가** 반영
  (`us_data.download_prices`가 장중 미완성 봉은 제외해 항상 마지막 정규 종가만 사용).
- **한국**: 07:20 KST는 개장(09:00) 전이라 **직전 거래일 종가** 반영.

각 카드의 "YYYY-MM-DD 기준"은 그 데이터의 실제 마지막 종가일이다(수집 시각과 별개).

### ⚠️ 실측 주의사항
- **cron은 정시 보장이 아니다(best-effort).** 실측상 예약 22:20 UTC 대비 **약 55~80분
  지연**되어 실행된 사례가 있다(실제 착지: KST 08:00~08:40 이후). GitHub 부하 시 더 늦어질 수 있다.
- **요일 정렬(`0-4`)은 2026-07-13에 수정됨.** 이전 `1-5`(UTC 월~금)는 KST 월요일이
  스킵되고 불필요한 KST 토요일에 실행되는 버그가 있었다. 지금은 KST 월~금에 정확히 착지한다.
- **60일간 리포 활동이 없으면** GitHub가 예약 워크플로를 자동 비활성화한다.
- **수동 실행**: Actions 탭 → "Scout market scan" → *Run workflow*(workflow_dispatch).

## 원본과의 관계 (중요)

`scripts/` 안의 스캔 코드는 **`C:\___AI Workspace\claude code_ws\stock-scout\scripts`
의 미러**다. stock-scout 는 git 리포가 아니라 로컬 폴더라 Actions 에서 직접
쓸 수 없어 이 리포에 복사해 둔 것이다.

- **원본(authoring)**: `stock-scout/scripts/*.py`
- **미러(cloud)**: `stock-dashboard/scout/engine/scripts/*.py`

원본에서 스캔 로직(scan_kr / scan_us / screen_growth / common / kr_data / us_data)을
수정하면 아래로 동기화할 것:

```powershell
$src = "C:\___AI Workspace\claude code_ws\stock-scout\scripts"
$dst = "C:\___AI Workspace\claude code_ws\stock-dashboard\scout\engine\scripts"
"common.py","kr_data.py","us_data.py","scan_kr.py","scan_us.py","screen_growth.py" |
  ForEach-Object { Copy-Item "$src\$_" "$dst\$_" -Force }
```

## 산출물 소유 (클라우드 전용, 2026-07-13부터)

| 산출물 | 실행 위치 |
|---|---|
| kr_scan / us_scan / kr_screen / us_screen | GitHub Actions (`scout-scan.yml`) |

과거엔 insights(정성 분석)·성적표·리포트 HTML을 로컬 Claude 세션이 별도로 발행하는
하이브리드 구조였으나, 그 기능은 제거되었다(2026-07-13). 이제 `publish_scan.py`가
`scout/data/manifest.json`의 유일한 발행자다.

## 산출물 (git 미추적)

`scout/engine/output/`, `scout/engine/data/` 는 스캔 중 생성되는 임시 파일이라
`.gitignore` 로 제외한다. 발행되는 것은 `scout/data/` 뿐이다.
