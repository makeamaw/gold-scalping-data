"""
Scalping Strategy Engine — รัวเร็ว style
M1 เป็น primary trigger (BUY + SELL), M15 เป็น bonus score เท่านั้น
"""
import logging
import config

logger = logging.getLogger(__name__)


def _get_direction(analysis: dict) -> str:
    """
    กำหนด direction จาก M1 เป็นหลัก — ไม่ lock ตาม M15 อีกต่อไป
    BUY/SELL ได้ทั้งคู่ตาม short-term momentum
    """
    m1 = analysis.get("m1", {})
    m5 = analysis.get("m5", {})

    # 1. M1 structure break — ชัดเจนที่สุด
    if m1.get("structure_break"):
        return m1.get("direction", "NONE")

    # 2. M1 momentum candle ไม่มี structure break → ดู candle body direction
    if m1.get("momentum_candle"):
        lc = m1.get("last_close", 0)
        lo = m1.get("last_open", 0)
        if lc and lo and lc != lo:
            return "BUY" if lc > lo else "SELL"

    return "NONE"


def calculate_confidence(analysis: dict, spread_ok: bool, direction: str) -> tuple[int, dict]:
    """
    Score system ใหม่ — M1 primary (45), M5 confirm (30), M15 bonus (15)
    Threshold 55: ต้องผ่าน M1 trigger + อย่างน้อยหนึ่งอย่าง
    """
    breakdown = {
        "m1_trigger":      0,
        "m5_momentum":     0,
        "m15_trend_align": 0,
        "volume_spike":    0,
        "spread_good":     0,
    }

    m15 = analysis.get("m15", {})
    m5  = analysis.get("m5",  {})
    m1  = analysis.get("m1",  {})

    # ── M1 Trigger (+45) ──────────────────────────────────────
    structure_match = (
        m1.get("structure_break", False)
        and m1.get("direction", "NONE") == direction
    )
    # momentum candle ในทิศเดียวกับ direction
    mc = m1.get("momentum_candle", False)
    mc_dir_match = False
    if mc:
        lc, lo = m1.get("last_close", 0), m1.get("last_open", 0)
        if lc and lo:
            mc_dir_match = (direction == "BUY" and lc > lo) or (direction == "SELL" and lc < lo)

    if structure_match or mc_dir_match:
        breakdown["m1_trigger"] = config.SCORE_M1_TRIGGER

    # ── M5 Momentum (+30) — RSI มี room ในทิศที่จะไป ──────────
    rsi = m5.get("rsi", 50) or 50
    pullback = m5.get("pullback", False)

    if direction == "BUY":
        # RSI ไม่ overbought → ยังมีแรงขึ้น
        if rsi < config.RSI_OVERBOUGHT or pullback:
            breakdown["m5_momentum"] = config.SCORE_M5_MOMENTUM
    elif direction == "SELL":
        # RSI ไม่ oversold → ยังมีแรงลง
        if rsi > config.RSI_OVERSOLD or pullback:
            breakdown["m5_momentum"] = config.SCORE_M5_MOMENTUM

    # ── M15 Bonus (+15) — เทรนตรงได้ bonus ──────────────────
    bias = m15.get("bias", "NEUTRAL")
    if (bias == "BULLISH" and direction == "BUY") or (bias == "BEARISH" and direction == "SELL"):
        breakdown["m15_trend_align"] = config.SCORE_M15_TREND_ALIGN

    # ── Volume Spike (+5) ─────────────────────────────────────
    if m5.get("volume_spike"):
        breakdown["volume_spike"] = config.SCORE_VOLUME_SPIKE

    # ── Spread OK (+5) ────────────────────────────────────────
    if spread_ok:
        breakdown["spread_good"] = config.SCORE_SPREAD_GOOD

    total = sum(breakdown.values())
    return total, breakdown


def generate_signal(analysis: dict, spread_ok: bool) -> dict:
    """
    สร้างสัญญาณเทรด — รัวเร็ว: M1 ยิง → เข้าทันที
    """
    direction = _get_direction(analysis)

    if direction == "NONE":
        return {
            "signal": "NONE",
            "score": 0,
            "breakdown": {},
            "reason": "No M1 trigger",
        }

    score, breakdown = calculate_confidence(analysis, spread_ok, direction)

    if score < config.CONFIDENCE_THRESHOLD:
        return {
            "signal": "NONE",
            "score": score,
            "breakdown": breakdown,
            "reason": f"Score {score} < {config.CONFIDENCE_THRESHOLD}",
        }

    bias = analysis.get("m15", {}).get("bias", "NEUTRAL")
    trend_tag = "WITH-TREND" if (
        (bias == "BULLISH" and direction == "BUY") or
        (bias == "BEARISH" and direction == "SELL")
    ) else "COUNTER-TREND"

    return {
        "signal": direction,
        "score": score,
        "breakdown": breakdown,
        "reason": f"Score {score} | M1 {direction} | {trend_tag}",
        "bias": bias,
        "pullback": analysis.get("m5", {}).get("pullback", False),
    }


def calculate_sl_tp(
    signal: str,
    entry_price: float,
    point: float,
    sl_points: int | None = None,
    tp_points: int | None = None,
) -> tuple[float, float]:
    """คำนวณ SL/TP — ค่ากลาง range"""
    if sl_points is None:
        sl_points = (config.SL_MIN_POINTS + config.SL_MAX_POINTS) // 2  # 1250

    if tp_points is None:
        tp_points = (config.TP_MIN_POINTS + config.TP_MAX_POINTS) // 2  # 2000

    sl_dist = sl_points * point
    tp_dist = tp_points * point

    if signal == "BUY":
        sl = round(entry_price - sl_dist, 2)
        tp = round(entry_price + tp_dist, 2)
    else:
        sl = round(entry_price + sl_dist, 2)
        tp = round(entry_price - tp_dist, 2)

    return sl, tp
