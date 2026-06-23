# 📈 2026 글로벌 주가 대시보드 (미국 · 한국 · 일본)

2026년 **각국 개장일 종가** 대비 **2개월 말 / 4개월 말 / 현재** 시점의 주가와 상승률을
한 화면에서 보여주는 정적 웹 대시보드입니다. 티커·종목명 검색과 시장별 필터를 제공합니다.

- **미국**: 대형주(S&P500/나스닥 주요) 큐레이션 — Yahoo Finance
- **일본**: 닛케이225 주요 종목 큐레이션 — Yahoo Finance (`.T`)
- **한국**: KOSPI/KOSDAQ **전체** — FinanceDataReader(네이버 기반)
- 데이터는 **GitHub Actions 가 매일 자동 갱신**(`data/data.json` 커밋)

---

## 구조

```
stock-dashboard/
├─ index.html                # 대시보드 페이지
├─ assets/
│  ├─ style.css
│  └─ app.js                 # 검색·필터·정렬·상세 (바닐라 JS)
├─ data/
│  └─ data.json              # 수집 결과 (Actions 가 갱신)
├─ scripts/
│  ├─ config.py              # 미·일 종목 유니버스, 기준 시점
│  └─ fetch_data.py          # 데이터 수집기
├─ .github/workflows/
│  └─ update-data.yml        # 매일 자동 갱신 워크플로
└─ requirements.txt
```

## 기준 시점 정의 (국가별 실제 거래일)

| 구분 | 의미 |
|------|------|
| 개장일 | 2026년 첫 거래일 (미 1/2, 한 1/2, 일 1/5 등) |
| 2개월말 | 2월 마지막 거래일 |
| 4개월말 | 4월 마지막 거래일 |
| 현재 | 최근 거래일 |

상승률(%) = `(해당 시점 종가 / 개장일 종가 − 1) × 100`, 수정주가(배당·액면 반영) 기준.
색상은 한국식 관례(상승=빨강 🔴, 하락=파랑 🔵)를 따릅니다.

---

## 로컬에서 데이터 생성

```bash
pip install -r requirements.txt
python scripts/fetch_data.py      # data/data.json 생성
```

로컬 미리보기(정적 서버 필요 — fetch 는 file:// 에서 막힘):

```bash
python -m http.server 8000
# 브라우저에서 http://localhost:8000 접속
```

---

## GitHub Pages 배포 (한 번만 설정)

1. **새 저장소 생성** 후 이 폴더 내용을 푸시
   ```bash
   cd stock-dashboard
   git init
   git add .
   git commit -m "init: 2026 글로벌 주가 대시보드"
   git branch -M main
   git remote add origin https://github.com/<사용자명>/<저장소명>.git
   git push -u origin main
   ```

2. **GitHub Pages 활성화**
   저장소 → **Settings → Pages** → *Build and deployment* → Source = **Deploy from a branch**
   → Branch = `main`, 폴더 = `/ (root)` → Save
   → 잠시 후 `https://<사용자명>.github.io/<저장소명>/` 에서 접속

3. **자동 갱신 권한 확인**
   Settings → **Actions → General → Workflow permissions** → **Read and write permissions** 체크

4. **첫 데이터 채우기 (수동 1회 실행)**
   Actions 탭 → *Update stock data* → **Run workflow**
   (이후 매일 22:00 UTC = 한국시간 07:00 자동 실행)

> 참고: GitHub Actions 러너는 미국 IP라 KRX 직접 API(pykrx)는 차단될 수 있습니다.
> 본 프로젝트는 네이버 기반 FinanceDataReader 를 사용해 이 문제를 회피합니다.

---

## 갱신 주기 / 커스터마이징

- **주기 변경**: `.github/workflows/update-data.yml` 의 `cron` 수정
- **미국·일본 종목 추가**: `scripts/config.py` 의 `US_STOCKS` / `JP_STOCKS` 딕셔너리 편집
- **한국 범위**: 기본은 KOSPI+KOSDAQ 전체. KONEX/ETF 는 제외

## 면책

투자 참고용 자료이며 데이터 정확성·실시간성을 보장하지 않습니다. 투자 판단의 책임은 이용자에게 있습니다.
