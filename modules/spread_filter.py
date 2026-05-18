"""
Spread Filter — ตรวจสอบ spread ก่อนอนุญาตเปิดออเดอร์
"""
import logging
import config

logger = logging.getLogger(__name__)


def is_spread_ok(tick: dict) -> bool:
    if tick is None:
        logger.warning("No tick data — blocking trade")
        return False

    spread = tick.get("spread", 9999)
    ok = spread <= config.MAX_SPREAD_POINTS

    if not ok:
        logger.debug(f"Spread too high: {spread} > {config.MAX_SPREAD_POINTS}")

    return ok


def get_spread_status(tick: dict) -> str:
    if tick is None:
        return "N/A"
    spread = tick.get("spread", 0)
    if spread <= config.MAX_SPREAD_POINTS * 0.7:
        return f"Low ({spread})"
    elif spread <= config.MAX_SPREAD_POINTS:
        return f"Normal ({spread})"
    else:
        return f"HIGH ({spread}) ⚠️"
