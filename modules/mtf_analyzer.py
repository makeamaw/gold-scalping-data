"""
Multi-Timeframe Analyzer — EMA, RSI, Volume, Momentum per TF
ใช้ library 'ta' (รองรับ Python 3.11)
"""
import pandas as pd
import ta
import logging
import config
from modules.market_reader import get_ohlcv

logger = logging.getLogger(__name__)


def analyze_m15(symbol: str) -> dict:
    """M15: trend bias via EMA50/EMA200"""
    df = get_ohlcv(symbol, "M15", 300)

    if df.empty or len(df) < config.EMA_SLOW + 5:
        return {"bias": "NEUTRAL", "ema_fast": None, "ema_slow": None, "close": None}

    df = df.copy()
    df["ema_fast"] = ta.trend.ema_indicator(df["close"], window=config.EMA_FAST)
    df["ema_slow"] = ta.trend.ema_indicator(df["close"], window=config.EMA_SLOW)

    last = df.iloc[-1]
    if pd.isna(last["ema_fast"]) or pd.isna(last["ema_slow"]):
        return {"bias": "NEUTRAL", "ema_fast": None, "ema_slow": None, "close": round(last["close"], 3)}

    if last["ema_fast"] > last["ema_slow"]:
        bias = "BULLISH"
    elif last["ema_fast"] < last["ema_slow"]:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    return {
        "bias": bias,
        "ema_fast": round(last["ema_fast"], 3),
        "ema_slow": round(last["ema_slow"], 3),
        "close": round(last["close"], 3),
    }


def analyze_m5(symbol: str) -> dict:
    """M5: RSI momentum, volume spike, pullback — ใช้ 100 bars"""
    df = get_ohlcv(symbol, "M5", 100)

    default = {"rsi": None, "volume_spike": False, "rsi_signal": "NEUTRAL", "pullback": False}

    if df.empty or len(df) < config.RSI_PERIOD + 5:
        return default

    df = df.copy()
    df["rsi"]    = ta.momentum.rsi(df["close"], window=config.RSI_PERIOD)
    df["vol_ma"] = df["tick_volume"].rolling(20).mean()

    last = df.iloc[-1]

    if pd.isna(last["rsi"]):
        return default

    rsi = last["rsi"]
    if rsi <= config.RSI_OVERSOLD:
        rsi_signal = "OVERSOLD"
    elif rsi >= config.RSI_OVERBOUGHT:
        rsi_signal = "OVERBOUGHT"
    else:
        rsi_signal = "NEUTRAL"

    volume_spike = (
        bool(last["tick_volume"] > last["vol_ma"] * 1.5)
        if not pd.isna(last["vol_ma"]) else False
    )

    prev3 = df.iloc[-4:-1]
    if len(prev3) >= 3:
        prev_close = prev3["close"].values
        pullback = bool(
            (prev_close[-1] < prev_close[0] and last["close"] > prev_close[-1])
            or (prev_close[-1] > prev_close[0] and last["close"] < prev_close[-1])
        )
    else:
        pullback = False

    return {
        "rsi": round(rsi, 1),
        "volume_spike": volume_spike,
        "rsi_signal": rsi_signal,
        "pullback": pullback,
    }


def analyze_m1(symbol: str) -> dict:
    """M1: structure break, momentum candle — ใช้ 30 bars"""
    df = get_ohlcv(symbol, "M1", 30)

    default = {"structure_break": False, "momentum_candle": False, "direction": "NONE",
               "last_close": None, "last_open": None}

    if df.empty or len(df) < 8:
        return default

    df = df.copy()
    df["body"]  = abs(df["close"] - df["open"])
    df["range"] = df["high"] - df["low"]

    last = df.iloc[-1]
    prev = df.iloc[-7:-1]

    avg_body  = prev["body"].mean()
    avg_range = prev["range"].mean()

    momentum_candle = bool(
        last["body"] > avg_body * 1.5
        and last["body"] > avg_range * 0.6
        and not pd.isna(avg_body)
    )

    recent_high = prev["high"].max()
    recent_low  = prev["low"].min()

    if last["close"] > recent_high:
        structure_break, direction = True, "BUY"
    elif last["close"] < recent_low:
        structure_break, direction = True, "SELL"
    else:
        structure_break, direction = False, "NONE"

    return {
        "structure_break": structure_break,
        "momentum_candle": momentum_candle,
        "direction": direction,
        "last_close": round(last["close"], 3),
        "last_open": round(last["open"], 3),
    }


def get_full_analysis(symbol: str) -> dict:
    m15 = analyze_m15(symbol)
    m5  = analyze_m5(symbol)
    m1  = analyze_m1(symbol)
    return {"m15": m15, "m5": m5, "m1": m1}
