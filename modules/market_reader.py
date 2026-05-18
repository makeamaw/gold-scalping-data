"""
Market Reader — MT5 connection, OHLCV data, tick data
"""
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import logging
import config

logger = logging.getLogger(__name__)

TF_MAP = {
    "M1":  mt5.TIMEFRAME_M1,
    "M5":  mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1":  mt5.TIMEFRAME_H1,
}


def connect() -> bool:
    if not mt5.initialize():
        logger.error(f"MT5 initialize failed: {mt5.last_error()}")
        return False

    if config.MT5_LOGIN and config.MT5_PASSWORD:
        ok = mt5.login(
            login=config.MT5_LOGIN,
            password=config.MT5_PASSWORD,
            server=config.MT5_SERVER,
        )
        if not ok:
            logger.error(f"MT5 login failed: {mt5.last_error()}")
            mt5.shutdown()
            return False

    info = mt5.account_info()
    if info is None:
        logger.error("Cannot get account info")
        return False

    logger.info(
        f"Connected | Account: {info.login} | "
        f"Balance: {info.balance:.2f} | Server: {info.server}"
    )
    return True


def disconnect():
    mt5.shutdown()
    logger.info("MT5 disconnected")


def get_ohlcv(symbol: str, timeframe: str, bars: int = 300) -> pd.DataFrame:
    tf = TF_MAP.get(timeframe)
    if tf is None:
        raise ValueError(f"Unknown timeframe: {timeframe}")

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
    if rates is None or len(rates) == 0:
        logger.warning(f"No rates for {symbol} {timeframe}")
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("time", inplace=True)
    return df


def get_tick(symbol: str) -> dict | None:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    return {
        "bid": tick.bid,
        "ask": tick.ask,
        "spread": round((tick.ask - tick.bid) / mt5.symbol_info(symbol).point),
        "time": datetime.fromtimestamp(tick.time),
    }


def get_account_info() -> dict | None:
    info = mt5.account_info()
    if info is None:
        return None
    return {
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "free_margin": info.margin_free,
        "profit": info.profit,
        "currency": info.currency,
    }


def get_open_positions(symbol: str) -> list[dict]:
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        return []
    result = []
    for p in positions:
        result.append({
            "ticket": p.ticket,
            "type": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
            "volume": p.volume,
            "open_price": p.price_open,
            "sl": p.sl,
            "tp": p.tp,
            "profit": p.profit,
            "open_time": datetime.fromtimestamp(p.time),
        })
    return result


def get_symbol_info(symbol: str) -> dict | None:
    info = mt5.symbol_info(symbol)
    if info is None:
        return None
    return {
        "point": info.point,
        "digits": info.digits,
        "trade_contract_size": info.trade_contract_size,
        "volume_min": info.volume_min,
        "volume_step": info.volume_step,
    }
