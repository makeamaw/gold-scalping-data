"""
Trade Executor — Place, modify, and close orders on MT5
"""
import MetaTrader5 as mt5
import logging
from datetime import datetime
import config

logger = logging.getLogger(__name__)


def _get_point(symbol: str) -> float:
    info = mt5.symbol_info(symbol)
    return info.point if info else 0.0001


def open_order(
    symbol: str,
    signal: str,
    lot: float,
    sl: float,
    tp: float,
    comment: str = "GoldScalp",
) -> dict | None:
    """
    เปิดออเดอร์ BUY หรือ SELL
    Returns: dict ข้อมูล order ถ้าสำเร็จ, None ถ้าล้มเหลว
    """
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        logger.error(f"Cannot get tick for {symbol}")
        return None

    order_type = mt5.ORDER_TYPE_BUY if signal == "BUY" else mt5.ORDER_TYPE_SELL
    price      = tick.ask if signal == "BUY" else tick.bid

    request = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       symbol,
        "volume":       lot,
        "type":         order_type,
        "price":        price,
        "sl":           sl,
        "tp":           tp,
        "deviation":    10,
        "magic":        20240101,
        "comment":      comment,
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code = result.retcode if result else "None"
        logger.error(f"Order failed | {signal} {symbol} | code: {code}")
        return None

    spread = round((tick.ask - tick.bid) / _get_point(symbol))
    logger.info(
        f"Order opened | #{result.order} {signal} {lot} {symbol} "
        f"@ {price:.2f} | SL:{sl:.2f} TP:{tp:.2f} | Spread:{spread}"
    )
    return {
        "ticket":     result.order,
        "symbol":     symbol,
        "type":       signal,
        "lot":        lot,
        "entry_price": price,
        "sl":         sl,
        "tp":         tp,
        "spread":     spread,
        "open_time":  datetime.now(),
    }


def close_order(ticket: int, symbol: str, lot: float, order_type: str) -> bool:
    """ปิดออเดอร์ด้วย ticket"""
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return False

    close_type  = mt5.ORDER_TYPE_SELL if order_type == "BUY" else mt5.ORDER_TYPE_BUY
    close_price = tick.bid if order_type == "BUY" else tick.ask

    request = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       symbol,
        "volume":       lot,
        "type":         close_type,
        "position":     ticket,
        "price":        close_price,
        "deviation":    10,
        "magic":        20240101,
        "comment":      "GoldScalp close",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code = result.retcode if result else "None"
        logger.error(f"Close failed | #{ticket} | code: {code}")
        return False

    logger.info(f"Order closed | #{ticket} @ {close_price:.2f}")
    return True


def get_closed_deals_today(symbol: str) -> list[dict]:
    """ดึงประวัติออเดอร์วันนี้"""
    from datetime import date, timedelta
    today = datetime.combine(date.today(), datetime.min.time())
    tomorrow = today + timedelta(days=1)

    deals = mt5.history_deals_get(today, tomorrow)
    if deals is None:
        return []

    result = []
    for d in deals:
        if d.symbol != symbol or d.entry != mt5.DEAL_ENTRY_OUT:
            continue
        result.append({
            "ticket":  d.ticket,
            "type":    "BUY" if d.type == mt5.DEAL_TYPE_BUY else "SELL",
            "volume":  d.volume,
            "price":   d.price,
            "profit":  d.profit,
            "time":    datetime.fromtimestamp(d.time),
            "comment": d.comment,
        })
    return result
