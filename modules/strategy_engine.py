"""
Scalping Strategy Engine — Confidence Score + Signal Generation
"""
import logging
import config

logger = logging.getLogger(__name__)


def calculate_confidence(analysis: dict, spread_ok: bool) -> tuple[int, dict]:
    """
    คำนวณ Confidence Score จากผลวิเคราะห์ทุก timeframe
    Returns: (total_score, breakdown_dict)
    """
    breakdown = {
        "m15_trend_align": 0,
        "m5_rsi_confirm":  0,
        "volume_spike":    0,
        "spread_good":     0,
        "momentum_candle": 0,
    }

    m15 = analysis.get("m15", {})
    m5  = analysis.get("m5",  {})
    m1  = analysis.get("m1",  {})

    bias      = m15.get("bias", "NEUTRAL")
    direction = m1.get("direction", "NONE")

    # M15 Trend Align — ทิศ M15 ตรงกับสัญญาณ M1
    if bias == "BULLISH" and direction == "BUY":
        breakdown["m15_trend_align"] = config.SCORE_M15_TREND_ALIGN
    elif bias == "BEARISH" and direction == "SELL":
        breakdown["m15_trend_align"] = config.SCORE_M15_TREND_ALIGN

    # M5 RSI Confirm
    rsi_signal = m5.get("rsi_signal", "NEUTRAL")
    if direction == "BUY" and rsi_signal == "OVERSOLD":
        breakdown["m5_rsi_confirm"] = config.SCORE_M5_RSI_CONFIRM
    elif direction == "SELL" and rsi_signal == "OVERBOUGHT":
        breakdown["m5_rsi_confirm"] = config.SCORE_M5_RSI_CONFIRM
    elif rsi_signal == "NEUTRAL":
        # RSI กลางๆ ก็ให้คะแนนบางส่วน
        breakdown["m5_rsi_confirm"] = config.SCORE_M5_RSI_CONFIRM // 2

    # Volume Spike
    if m5.get("volume_spike"):
        breakdown["volume_spike"] = config.SCORE_VOLUME_SPIKE

    # Spread Good
    if spread_ok:
        breakdown["spread_good"] = config.SCORE_SPREAD_GOOD

    # Momentum Candle (M1)
    if m1.get("momentum_candle"):
        breakdown["momentum_candle"] = config.SCORE_MOMENTUM_CANDLE

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
    m1  = analysis.get("m1", {})
    m15 = analysis.get("m15", {})

    direction = m1.get("direction", "NONE")
    structure = m1.get("structure_break", False)

    if direction == "NONE" or not structure:
        return {
            "signal": "NONE",
            "score": 0,
            "breakdown": {},
            "reason": "No structure break on M1",
        }

    score, breakdown = calculate_confidence(analysis, spread_ok)

    if score < config.CONFIDENCE_THRESHOLD:
        return {
            "signal": "NONE",
            "score": score,
            "breakdown": breakdown,
            "reason": f"Score {score} < threshold {config.CONFIDENCE_THRESHOLD}",
        }

    bias = m15.get("bias", "NEUTRAL")
    if bias == "NEUTRAL":
        # Counter-trend ใน sideways — ลด score เพิ่มเติม แต่ยังผ่านได้
        logger.debug("M15 NEUTRAL — sideways market, proceed with caution")

    return {
        "signal": direction,
        "score": score,
        "breakdown": breakdown,
        "reason": f"Score {score} | Bias {bias} | M1 {direction}",
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
    """
    คำนวณ SL และ TP จาก entry price
    ใช้ค่ากลางของ range ถ้าไม่ระบุ
    """
    if sl_points is None:
        sl_points = (config.SL_MIN_POINTS + config.SL_MAX_POINTS) // 2  # 115

    if tp_points is None:
        tp_points = (config.TP_MIN_POINTS + config.TP_MAX_POINTS) // 2  # 175

    sl_dist = sl_points * point
    tp_dist = tp_points * point

    if signal == "BUY":
        sl = round(entry_price - sl_dist, 2)
        tp = round(entry_price + tp_dist, 2)
    else:  # SELL
        sl = round(entry_price + sl_dist, 2)
        tp = round(entry_price - tp_dist, 2)

    return sl, tp
