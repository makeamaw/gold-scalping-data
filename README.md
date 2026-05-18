# Adaptive Multi-Timeframe Gold Scalping Engine

ระบบออโต้เทรด XAUUSD บน MT5 แบบ Scalping ด้วย Multi-Timeframe Confirmation

## โครงสร้างโปรเจกต์

```
GoldScalpingEngine/
├── config.py               ← การตั้งค่าทั้งหมด (แก้ที่นี่ก่อน)
├── main.py                 ← รัน Engine หลัก
├── requirements.txt
├── modules/
│   ├── market_reader.py    ← เชื่อมต่อ MT5, ดึงข้อมูล
│   ├── mtf_analyzer.py     ← วิเคราะห์ M1/M5/M15
│   ├── strategy_engine.py  ← Confidence Score + สัญญาณ
│   ├── risk_manager.py     ← Daily limit, equity protection
│   ├── trade_executor.py   ← เปิด/ปิดออเดอร์
│   ├── journal_logger.py   ← บันทึก SQLite
│   ├── ai_analytics.py     ← วิเคราะห์ย้อนหลัง
│   ├── telegram_reporter.py← ส่ง Report
│   └── spread_filter.py    ← ตรวจ Spread
├── database/
│   └── trades.db           ← Auto-created
└── logs/
    └── engine.log          ← Auto-created
```

## การติดตั้ง

### 1. ติดตั้ง Python dependencies

```bash
pip install -r requirements.txt
```

### 2. ตั้งค่าใน `config.py`

```python
# MT5 Account
MT5_LOGIN    = 1234567        # Account number
MT5_PASSWORD = "your_pass"
MT5_SERVER   = "Exness-Trial3"

# Telegram (ขอ token จาก @BotFather, chat_id จาก @userinfobot)
TELEGRAM_BOT_TOKEN = "1234567890:ABCdef..."
TELEGRAM_CHAT_ID   = "123456789"

# Symbol (ตรวจสอบใน MT5 ว่าใช้ XAUUSD หรือ XAUUSDm)
SYMBOL = "XAUUSDm"
```

### 3. รันระบบ

```bash
python main.py
```

## Logic หลัก

### Confidence Score (ต้อง >= 75 จึงเปิดออเดอร์)

| ปัจจัย | คะแนน |
|--------|--------|
| M15 Trend Align | 30 |
| M5 RSI Confirm | 20 |
| Volume Spike | 20 |
| Spread Good | 15 |
| Momentum Candle | 15 |

### Multi-Timeframe

- **M15** — EMA50 vs EMA200 → Bias (Bullish/Bearish)
- **M5** — RSI, Volume, Pullback → Momentum confirmation
- **M1** — Structure break, Momentum candle → Trigger

### Risk Management

- Daily Profit Target: +400 THB → หยุดเทรด
- Daily Max Loss: -150 THB → Lock session
- Max Open Trades: 2 ไม้พร้อมกัน
- Cooldown: 45 วินาทีหลังปิดออเดอร์

## AI Analytics

รัน manual ได้:
```python
from modules import ai_analytics
report = ai_analytics.suggest_parameters(days=14)
print(report)
```

AI จะเสนอ parameter แต่ **ไม่แก้อัตโนมัติ** — ต้องมนุษย์ approve ก่อน

## Telegram Setup

1. หา Bot Token: คุยกับ `@BotFather` → `/newbot`
2. หา Chat ID: ส่งข้อความให้ bot แล้วไปที่
   `https://api.telegram.org/bot<TOKEN>/getUpdates`

## หมายเหตุสำคัญ

- ทดสอบบน Demo Account เสมอก่อน Live
- ตรวจสอบชื่อ Symbol ให้ตรงกับ Broker (อาจเป็น XAUUSDm)
- ระบบต้องรันตลอดเวลา — แนะนำ VPS
