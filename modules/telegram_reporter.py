"""
Telegram Reporter — ส่ง report ทุก 15 นาทีและแจ้งเตือนสำคัญ
"""
import requests
import logging
from datetime import datetime
import config

logger = logging.getLogger(__name__)


def _send(text: str) -> bool:
    if config.TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.debug(f"[Telegram MOCK] {text[:80]}...")
        return True

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    config.TELEGRAM_CHAT_ID,
        "text":       text,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if not resp.ok:
            logger.warning(f"Telegram error: {resp.text[:200]}")
        return resp.ok
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")
        return False


def build_report(
    account: dict,
    risk_status: dict,
    analysis: dict,
    stats: dict,
    positions: list,
    spread_ok: bool,
    session_locked: bool,
) -> str:
    now    = datetime.now().strftime("%H:%M")
    status = "🔒 LOCKED" if session_locked else "✅ Running"
    bias   = analysis.get("m15", {}).get("bias", "NEUTRAL")
    rsi    = analysis.get("m5", {}).get("rsi", "-")

    balance    = account.get("balance", 0)
    equity     = account.get("equity", 0)
    floating   = account.get("profit", 0)
    today_pnl  = risk_status.get("today_pnl", 0)
    open_count = len(positions)
    winrate    = stats.get("winrate", 0)
    total      = stats.get("total_trades", 0)

    buy_count  = sum(1 for p in positions if p["type"] == "BUY")
    sell_count = sum(1 for p in positions if p["type"] == "SELL")

    spread_txt  = "✅ Normal" if spread_ok else "⚠️ High"
    pnl_icon    = "📈" if today_pnl >= 0 else "📉"
    bias_icon   = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "⚪"}.get(bias, "⚪")

    lines = [
        f"<b>⏰ [{now}] Gold Scalping Report</b>",
        f"",
        f"<b>Session:</b> {status}",
        f"<b>Balance:</b> {balance:.2f}",
        f"<b>Equity:</b>  {equity:.2f}",
        f"<b>Floating:</b> {floating:+.2f}",
        f"<b>{pnl_icon} Today PnL:</b> {today_pnl:+.2f}",
        f"",
        f"<b>Trades:</b> BUY×{buy_count} | SELL×{sell_count} | Open:{open_count}",
        f"<b>Today:</b> {total} trades | WR: {winrate:.1f}%",
        f"",
        f"<b>{bias_icon} Bias (M15):</b> {bias}",
        f"<b>RSI (M5):</b> {rsi}",
        f"<b>Spread:</b> {spread_txt}",
        f"",
        f"<b>Target:</b> {risk_status.get('progress_to_target', '-')}",
    ]

    if risk_status.get("locked"):
        lines.append(f"\n🚫 <b>Lock:</b> {risk_status.get('lock_reason', '')}")

    return "\n".join(lines)


def send_report(report_text: str) -> bool:
    return _send(report_text)


def send_alert(message: str) -> bool:
    return _send(f"⚡ <b>Alert</b>\n{message}")


def send_trade_open(trade: dict, score: int, reason: str) -> bool:
    direction = trade.get("type", "?")
    icon      = "🟢" if direction == "BUY" else "🔴"
    text = (
        f"{icon} <b>Trade Opened — {direction}</b>\n"
        f"Ticket: #{trade.get('ticket')}\n"
        f"Entry: {trade.get('entry_price'):.2f}\n"
        f"SL: {trade.get('sl'):.2f} | TP: {trade.get('tp'):.2f}\n"
        f"Score: {score}/100\n"
        f"Signal: {reason}"
    )
    return _send(text)


def send_trade_close(ticket: int, direction: str, profit: float) -> bool:
    icon   = "✅" if profit >= 0 else "❌"
    result = "WIN" if profit >= 0 else "LOSS"
    text = (
        f"{icon} <b>Trade Closed — {direction}</b>\n"
        f"Ticket: #{ticket}\n"
        f"PnL: {profit:+.2f}\n"
        f"Result: {result}"
    )
    return _send(text)
