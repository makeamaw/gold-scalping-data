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
DAILY_PROFIT_TARGET = 9999.0  # ปิด target ชั่วคราว — เก็บข้อมูล
DAILY_MAX_LOSS = 9999.0       # ปิด limit ชั่วคราว — เก็บข้อมูล

# ─── Equity Protection ────────────────────────────────────────
EQUITY_PROTECT_THRESHOLD = 250.0  # ถ้ากำไรเคยขึ้น +350 แล้ว Equity ลงต่ำกว่า +250 → หยุด
EQUITY_PROTECT_PEAK_TRIGGER = 350.0

# ─── Lot Management ───────────────────────────────────────────
INITIAL_LOT = 0.01
MAX_OPEN_TRADES = 4  # pyramid: เพิ่มได้ระหว่างมีไม้ค้าง

# ─── SL / TP (points) — รัวเร็ว style: SL กว้างพอหายใจ ─────────
SL_MIN_POINTS = 1000   # 1000pts = $1.00 SL (ห่างพอสำหรับ noise)
SL_MAX_POINTS = 1500   # 1500pts = $1.50 SL
TP_MIN_POINTS = 1500   # 1500pts = $1.50 TP
TP_MAX_POINTS = 2500   # 2500pts = $2.50 TP

# ─── Spread Filter ────────────────────────────────────────────
MAX_SPREAD_POINTS = 400  # รับ spread ได้กว้างขึ้นเล็กน้อย

# ─── Confidence Score — รัวเร็ว mode ─────────────────────────
CONFIDENCE_THRESHOLD = 55  # ลด threshold ให้ยิงบ่อยขึ้น

# ─── Score Weights — M1 เป็น primary trigger ─────────────────
SCORE_M1_TRIGGER      = 45  # primary: structure break / momentum candle
SCORE_M5_MOMENTUM     = 30  # RSI room + pullback confirm
SCORE_M15_TREND_ALIGN = 15  # bonus ถ้าเทรนตรง ไม่ใช่ gate
SCORE_VOLUME_SPIKE    =  5  # volume confirm
SCORE_SPREAD_GOOD     =  5  # spread ok

# ─── Indicators ───────────────────────────────────────────────
EMA_FAST = 50
EMA_SLOW = 200
RSI_PERIOD = 14
RSI_OVERBOUGHT = 60  # sensitive ขึ้น (เดิม 65)
RSI_OVERSOLD   = 40  # sensitive ขึ้น (เดิม 35)

# ─── Timeframes ───────────────────────────────────────────────
# ค่า MT5 timeframe constants จะถูก map ใน market_reader.py
TF_M1  = "M1"
TF_M5  = "M5"
TF_M15 = "M15"

# ─── Cooldown ─────────────────────────────────────────────────
COOLDOWN_SECONDS = 20  # รัวเร็ว: cooldown สั้นลง

# ─── Reporting ────────────────────────────────────────────────
REPORT_INTERVAL_MINUTES = 15

# ─── Telegram ─────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"   # ขอ Token จาก @BotFather
TELEGRAM_CHAT_ID   = "YOUR_CHAT_ID_HERE"     # หา Chat ID จาก @userinfobot

# ─── Database ─────────────────────────────────────────────────
DB_PATH  = r"C:\Users\nattawadee\GoldScalpingEngine\database\trades.db"

# ─── Logging ──────────────────────────────────────────────────
LOG_PATH = r"C:\Users\nattawadee\GoldScalpingEngine\logs\engine.log"
