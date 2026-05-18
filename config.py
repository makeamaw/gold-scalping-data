# =============================================================
# Adaptive Multi-Timeframe Gold Scalping Engine — Configuration
# =============================================================

# ─── MT5 Connection ───────────────────────────────────────────
MT5_LOGIN = 433627036
MT5_PASSWORD = "0969215608Ae/"
MT5_SERVER = "Exness-MT5Trial7"

# ─── Symbol ───────────────────────────────────────────────────
SYMBOL = "XAUUSDm"         # Exness ใช้ XAUUSDm (confirmed)

# ─── Account Info ─────────────────────────────────────────────
ACCOUNT_CURRENCY = "THB"
STARTING_BALANCE = 5000.0

# ─── Session Targets ──────────────────────────────────────────
DAILY_PROFIT_TARGET = 400.0   # หยุดเมื่อกำไรถึง (THB)
DAILY_MAX_LOSS = 150.0        # หยุดเมื่อขาดทุนถึง (THB)

# ─── Equity Protection ────────────────────────────────────────
EQUITY_PROTECT_THRESHOLD = 250.0  # ถ้ากำไรเคยขึ้น +350 แล้ว Equity ลงต่ำกว่า +250 → หยุด
EQUITY_PROTECT_PEAK_TRIGGER = 350.0

# ─── Lot Management ───────────────────────────────────────────
INITIAL_LOT = 0.01
MAX_OPEN_TRADES = 2

# ─── SL / TP (points) ─────────────────────────────────────────
SL_MIN_POINTS = 800    # XAUUSDm point=0.001 → 800pts = $0.80 SL
SL_MAX_POINTS = 1500   # 1500pts = $1.50 SL
TP_MIN_POINTS = 1000   # 1000pts = $1.00 TP
TP_MAX_POINTS = 2500   # 2500pts = $2.50 TP

# ─── Spread Filter ────────────────────────────────────────────
MAX_SPREAD_POINTS = 350  # XAUUSDm point=0.001 → 350pts = $0.35 spread

# ─── Confidence Score ─────────────────────────────────────────
CONFIDENCE_THRESHOLD = 75  # เข้าเทรดเมื่อ score >= 75

# ─── Score Weights ────────────────────────────────────────────
SCORE_M15_TREND_ALIGN = 30
SCORE_M5_RSI_CONFIRM  = 20
SCORE_VOLUME_SPIKE    = 20
SCORE_SPREAD_GOOD     = 15
SCORE_MOMENTUM_CANDLE = 15

# ─── Indicators ───────────────────────────────────────────────
EMA_FAST = 50
EMA_SLOW = 200
RSI_PERIOD = 14
RSI_OVERBOUGHT = 65
RSI_OVERSOLD = 35

# ─── Timeframes ───────────────────────────────────────────────
# ค่า MT5 timeframe constants จะถูก map ใน market_reader.py
TF_M1  = "M1"
TF_M5  = "M5"
TF_M15 = "M15"

# ─── Cooldown ─────────────────────────────────────────────────
COOLDOWN_SECONDS = 45  # หลังปิดออเดอร์รอกี่วินาที

# ─── Reporting ────────────────────────────────────────────────
REPORT_INTERVAL_MINUTES = 15

# ─── Telegram ─────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"   # ขอ Token จาก @BotFather
TELEGRAM_CHAT_ID   = "YOUR_CHAT_ID_HERE"     # หา Chat ID จาก @userinfobot

# ─── Database ─────────────────────────────────────────────────
DB_PATH  = r"C:\Users\nattawadee\GoldScalpingEngine\database\trades.db"

# ─── Logging ──────────────────────────────────────────────────
LOG_PATH = r"C:\Users\nattawadee\GoldScalpingEngine\logs\engine.log"
