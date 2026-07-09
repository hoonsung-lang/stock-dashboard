# scout/engine — 클라우드 스캔 엔진 (미러)

`scout-scan.yml` GitHub Actions 워크플로가 매 평일 아침 시장 스캔을 실행하는 코드다.
PC가 꺼져 있어도 시장 데이터(외국인/기관 수급·섹터 RS·모멘텀·성장주 스크리닝)는
클라우드에서 자동 갱신된다.

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

## 역할 분담 (하이브리드)

| 산출물 | 소유자 | 실행 위치 |
|---|---|---|
| kr_scan / us_scan / kr_screen / us_screen | 클라우드 | GitHub Actions (`scout-scan.yml`) |
| insights / call_performance / 리포트 HTML | Claude | 로컬 PC (앱 열려 있을 때, morning-brief 태스크) |

`publish_scan.py`(클라우드)와 `stock-scout/scripts/publish_web.py --insights-only`(로컬)는
`scout/data/manifest.json` 을 **merge** 방식으로 갱신해 서로의 항목을 덮어쓰지 않는다.

## 산출물 (git 미추적)

`scout/engine/output/`, `scout/engine/data/` 는 스캔 중 생성되는 임시 파일이라
`.gitignore` 로 제외한다. 발행되는 것은 `scout/data/` 뿐이다.
