# -*- coding: utf-8 -*-
"""
종목 유니버스 및 기준 시점 설정.

- 미국(US): 대형주 큐레이션 (S&P500 / 나스닥 주요)
- 일본(JP): 닛케이225 주요 종목 큐레이션
- 한국(KR): fetch_data.py 에서 pykrx/FDR 로 KOSPI/KOSDAQ 전체를 동적으로 수집

기준 연도: 2026년
"""

YEAR = 2026

# 한국: 시가총액 상위 N개를 '주요종목'으로 자동 선별 (전체 대신 큐레이션)
KR_TOP_KOSPI = 200
KR_TOP_KOSDAQ = 100

# 기준 시점 컷오프(해당 일자 이전의 마지막 거래일을 사용)
#  - open    : 연초 첫 거래일
#  - m2      : 2개월 말(2월 마지막 거래일)
#  - m4      : 4개월 말(4월 마지막 거래일)
#  - current : 최근 거래일
CUTOFFS = {
    "open": (YEAR, 1, 2),    # 첫 거래일 탐색 시작점
    "m2":   (YEAR, 2, 28),
    "m4":   (YEAR, 4, 30),
    # current 는 실행 시점(today)으로 동적 결정
}

# ---------------------------------------------------------------------------
# 미국 대형주 (티커: 종목명)
# ---------------------------------------------------------------------------
US_STOCKS = {
    "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet (A)", "AMZN": "Amazon",
    "NVDA": "NVIDIA", "META": "Meta Platforms", "TSLA": "Tesla", "AVGO": "Broadcom",
    "BRK-B": "Berkshire Hathaway", "JPM": "JPMorgan Chase", "V": "Visa", "MA": "Mastercard",
    "UNH": "UnitedHealth", "LLY": "Eli Lilly", "JNJ": "Johnson & Johnson", "XOM": "Exxon Mobil",
    "WMT": "Walmart", "PG": "Procter & Gamble", "HD": "Home Depot", "COST": "Costco",
    "ORCL": "Oracle", "MRK": "Merck", "ABBV": "AbbVie", "CVX": "Chevron",
    "KO": "Coca-Cola", "PEP": "PepsiCo", "BAC": "Bank of America", "ADBE": "Adobe",
    "CRM": "Salesforce", "AMD": "AMD", "NFLX": "Netflix", "TMO": "Thermo Fisher",
    "ACN": "Accenture", "MCD": "McDonald's", "ABT": "Abbott", "CSCO": "Cisco",
    "LIN": "Linde", "DHR": "Danaher", "INTC": "Intel", "QCOM": "Qualcomm",
    "TXN": "Texas Instruments", "WFC": "Wells Fargo", "PM": "Philip Morris", "NKE": "Nike",
    "VZ": "Verizon", "INTU": "Intuit", "AMGN": "Amgen", "IBM": "IBM",
    "CAT": "Caterpillar", "GE": "GE Aerospace", "DIS": "Walt Disney", "NOW": "ServiceNow",
    "UNP": "Union Pacific", "HON": "Honeywell", "SPGI": "S&P Global", "GS": "Goldman Sachs",
    "ISRG": "Intuitive Surgical", "AMAT": "Applied Materials", "BKNG": "Booking",
    "LOW": "Lowe's", "MS": "Morgan Stanley", "RTX": "RTX", "T": "AT&T",
    "PFE": "Pfizer", "BLK": "BlackRock", "AXP": "American Express", "ELV": "Elevance",
    "C": "Citigroup", "SYK": "Stryker", "DE": "Deere", "BA": "Boeing",
    "MDT": "Medtronic", "VRTX": "Vertex Pharma", "LMT": "Lockheed Martin", "ADP": "ADP",
    "TJX": "TJX", "MMC": "Marsh & McLennan", "GILD": "Gilead", "CB": "Chubb",
    "PLD": "Prologis", "MU": "Micron", "SNDK": "SanDisk", "SCHW": "Charles Schwab", "REGN": "Regeneron",
    "CI": "Cigna", "SO": "Southern Co", "BSX": "Boston Scientific", "ZTS": "Zoetis",
    "DUK": "Duke Energy", "PANW": "Palo Alto Networks", "MO": "Altria", "SLB": "Schlumberger",
    "BMY": "Bristol Myers", "EQIX": "Equinix", "CME": "CME Group", "PYPL": "PayPal",
    "SBUX": "Starbucks", "PGR": "Progressive", "APH": "Amphenol", "CDNS": "Cadence",
    "SNPS": "Synopsys", "KLAC": "KLA Corp", "LRCX": "Lam Research", "CMG": "Chipotle",
    "MRVL": "Marvell", "CRWD": "CrowdStrike", "SMCI": "Super Micro", "PLTR": "Palantir",
    "UBER": "Uber", "ABNB": "Airbnb", "COIN": "Coinbase", "SHOP": "Shopify",
    "SNOW": "Snowflake", "DELL": "Dell", "F": "Ford", "GM": "General Motors",
}

# ---------------------------------------------------------------------------
# 일본 주요주 (티커 숫자코드: 종목명) — yfinance 에는 ".T" 를 붙여 조회
# ---------------------------------------------------------------------------
JP_STOCKS = {
    "7203": "Toyota Motor", "6758": "Sony Group", "6861": "Keyence", "8306": "MUFG",
    "9984": "SoftBank Group", "6098": "Recruit Holdings", "9983": "Fast Retailing",
    "4063": "Shin-Etsu Chemical", "8035": "Tokyo Electron", "6501": "Hitachi",
    "7974": "Nintendo", "6902": "Denso", "9433": "KDDI", "9432": "NTT",
    "8058": "Mitsubishi Corp", "8001": "Itochu", "8031": "Mitsui & Co", "6594": "Nidec",
    "4519": "Chugai Pharma", "4568": "Daiichi Sankyo", "7741": "Hoya", "6367": "Daikin",
    "6273": "SMC", "6954": "Fanuc", "6981": "Murata Mfg", "7751": "Canon",
    "8316": "Sumitomo Mitsui FG", "8411": "Mizuho FG", "8766": "Tokio Marine",
    "2914": "Japan Tobacco", "4502": "Takeda Pharma", "4503": "Astellas Pharma",
    "4661": "Oriental Land", "6752": "Panasonic", "6701": "NEC", "6503": "Mitsubishi Electric",
    "7267": "Honda Motor", "7269": "Suzuki Motor", "7270": "Subaru", "7201": "Nissan Motor",
    "5108": "Bridgestone", "3382": "Seven & i", "9020": "JR East", "9022": "JR Central",
    "8053": "Sumitomo Corp", "8002": "Marubeni", "5401": "Nippon Steel", "5713": "Sumitomo Metal Mining",
    "4901": "Fujifilm", "4452": "Kao", "4911": "Shiseido", "2802": "Ajinomoto",
    "6857": "Advantest", "6920": "Lasertec", "6762": "TDK", "6645": "Omron",
    "8001x": "", "9101": "Nippon Yusen", "9104": "Mitsui OSK", "1605": "Inpex",
    "5020": "Eneos", "8801": "Mitsui Fudosan", "8802": "Mitsubishi Estate",
    "3659": "Nexon", "4307": "Nomura Research", "4689": "LY Corp", "9613": "NTT Data",
    "6981x": "", "7011": "Mitsubishi Heavy", "7012": "Kawasaki Heavy", "6326": "Kubota",
    "6301": "Komatsu", "8591": "ORIX", "8604": "Nomura Holdings", "4543": "Terumo",
    "4523": "Eisai", "2502": "Asahi Group", "2503": "Kirin Holdings",
}
# 빈 더미 키 제거
JP_STOCKS = {k: v for k, v in JP_STOCKS.items() if v}
