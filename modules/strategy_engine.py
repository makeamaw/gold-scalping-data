"""
Scalping Strategy Engine — Confidence Score + Signal Generation
"""
import logging
import config

logger = logging.getLogger(__name__)


def _get_direction(analysis: dict) -> str:
    """กำหนด direction จาก M15 bias เป็นหลัก, fallback M1"""
    bias = analysis.get("m15", {}).get("bias", "NEUTRAL")
    if bias == "BULLISH":
        return "BUY"
    if bias == "BEARISH":
        return "SELL"
    # NEUTRAL → ดู M1 structure break
    return analysis.get("m1", {}).get("direction", "NONE")


def calculate_confidence(analysis: dict, spread_ok: bool, direction: str) -> tuple[int, dict]:
    """
    คำนวณ Confidence Score จากผลวิเคราะห์ทุก timeframe
    Returns: (total_score, breakdown_dict)
    """
    breakdown = {
        "m15_trend_align": 0,
        "m5_momentum":     0,
        "m1_trigger":      0,
        "volume_spike":    0,
        "spread_good":     0,
    }

    m15 = analysis.get("m15", {})
    m5  = analysis.get("m5",  {})
    m1  = analysis.get("m1",  {})

    bias = m15.get("bias", "NEUTRAL")

    # M15 Trend Align (+30)
    if (bias == "BULLISH" and direction == "BUY") or (bias == "BEARISH" and direction == "SELL"):
        breakdown["m15_trend_align"] = config.SCORE_M15_TREND_ALIGN

    # M5 Momentum (+25) — RSI direction confirm หรือ pullback
    rsi       = m5.get("rsi", 50)
    rsi_signal = m5.get("rsi_signal", "NEUTRAL")
    pullback  = m5.get("pullback", False)

    if direction == "BUY":
        # RSI กำลังขึ้นจากโซน oversold หรือ neutral แต่ไม่ overbought
        rsi_confirm = rsi_signal in ("OVERSOLD", "NEUTRAL") and rsi is not None and rsi < 60
        if rsi_confirm or pullback:
            breakdown["m5_momentum"] = config.SCORE_M5_MOMENTUM
    elif direction == "SELL":
        rsi_confirm = rsi_signal in ("OVERBOUGHT", "NEUTRAL") and rsi is not None and rsi > 40
        if rsi_confirm or pullback:
            breakdown["m5_momentum"] = config.SCORE_M5_MOMENTUM

    # M1 Trigger (+20) — structure break หรือ momentum candle
    structure_match = (
        m1.get("structure_break", False)
        and m1.get("direction", "NONE") == direction
    )
    if structure_match or m1.get("momentum_candle", False):
        breakdown["m1_trigger"] = config.SCORE_M1_TRIGGER

    # Volume Spike (+15)
    if m5.get("volume_spike"):
        breakdown["volume_spike"] = config.SCORE_VOLUME_SPIKE

    # Spread Good (+10)
    if spread_ok:
        breakdown["spread_good"] = config.SCORE_SPREAD_GOOD

    total = sum(breakdown.values())
    return total, breakdown


def generate_signal(analysis: dict, spread_ok: bool) -> dict:
    """
    สร้างสัญญาณเทรด พร้อม score และ direction
    Returns: {
        "signal": "BUY" | "SELL" | "NONE",
        "score": int,
        "breakdown": dict,
        "reason": str
    }
    """
    direction = _get_direction(analysis)

    if direction == "NONE":
        return {
            "signal": "NONE",
            "score": 0,
            "breakdown": {},
            "reason": "M15 NEUTRAL and no M1 structure break",
        }

    score, breakdown = calculate_confidence(analysis, spread_ok, direction)

    if score < config.CONFIDENCE_THRESHOLD:
        return {
            "signal": "NONE",
            "score": score,
            "breakdown": breakdown,
            "reason": f"Score {score} < threshold {config.CONFIDENCE_THRESHOLD}",
        }

    bias = analysis.get("m15", {}).get("bias", "NEUTRAL")
    return {
        "signal": direction,
        "score": score,
        "breakdown": breakdown,
        "reason": f"Score {score} | Bias {bias} | Dir {direction}",
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
    """คำนวณ SL และ TP จาก entry price ใช้ค่ากลางของ range ถ้าไม่ระบุ"""
    if sl_points is None:
        sl_points = (config.SL_MIN_POINTS + config.SL_MAX_POINTS) // 2

    if tp_points is None:
        tp_points = (config.TP_MIN_POINTS + config.TP_MAX_POINTS) // 2

    sl_dist = sl_points * point
    tp_dist = tp_points * point

    if signal == "BUY":
        sl = round(entry_price - sl_dist, 2)
        tp = round(entry_price + tp_dist, 2)
    else:  # SELL
        sl = round(entry_price + sl_dist, 2)
        tp = round(entry_price - tp_dist, 2)

    return sl, tp
