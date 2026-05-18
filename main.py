"""
Adaptive Multi-Timeframe Gold Scalping Engine — Main Loop
"""
import time
import logging
import signal
import sys
import os
import subprocess
from datetime import datetime, date

import config
from modules import market_reader as mr
from modules import mtf_analyzer
from modules import strategy_engine as se
from modules import risk_manager as rm_module
from modules import trade_executor as te
from modules import journal_logger as jl
from modules import telegram_reporter as tg
from modules import spread_filter
from modules import ai_analytics
import export_summary

# ─── Logging Setup ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("main")

# ─── PID Lock ────────────────────────────────────────────────
PID_FILE = r"C:\Users\nattawadee\GoldScalpingEngine\engine.pid"


def _pid_running(pid: int) -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True
        )
        return str(pid) in result.stdout
    except Exception:
        return False


def acquire_lock() -> bool:
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                old_pid = int(f.read().strip())
            if _pid_running(old_pid):
                logger.critical(f"Engine already running (PID {old_pid}). Exiting.")
                return False
        except Exception:
            pass
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    return True


def release_lock():
    try:
        os.remove(PID_FILE)
    except Exception:
        pass


# ─── Global State ─────────────────────────────────────────────
risk_mgr = rm_module.RiskManager()
running   = True
last_report_time: datetime | None = None
active_trades: dict[int, dict] = {}   # ticket → trade info


def shutdown(sig, frame):
    global running
    logger.info("Shutdown signal received")
    running = False


signal.signal(signal.SIGINT,  shutdown)
signal.signal(signal.SIGTERM, shutdown)


def check_and_close_positions(positions: list[dict], account: dict):
    """ตรวจสอบออเดอร์ที่ปิดไปแล้วนอก EA (TP/SL hit)"""
    open_tickets = {p["ticket"] for p in positions}
    closed = [t for t in list(active_trades.keys()) if t not in open_tickets]

    for ticket in closed:
        trade = active_trades.pop(ticket, {})
        deals = te.get_closed_deals_today(config.SYMBOL)
        deal  = next((d for d in deals if d["position_id"] == ticket), None)
        profit = deal["profit"] if deal else 0.0
        exit_price = deal["price"] if deal else 0.0
        exit_time  = deal["time"] if deal else datetime.now()

        jl.log_trade_close(ticket, exit_price, profit, exit_time)
        tg.send_trade_close(ticket, trade.get("type", "?"), profit)
        risk_mgr.on_trade_closed()
        logger.info(f"Trade #{ticket} closed | PnL: {profit:+.2f}")


def try_open_trade(analysis: dict, tick: dict, account: dict, actual_open: int):
    """ประเมินสัญญาณและเปิดออเดอร์ถ้าผ่าน"""
    spread_ok = spread_filter.is_spread_ok(tick)
    signal    = se.generate_signal(analysis, spread_ok)

    if signal["signal"] == "NONE":
        logger.debug(f"No signal: {signal['reason']}")
        return

    # ใช้ actual MT5 positions แทน internal counter
    if actual_open >= config.MAX_OPEN_TRADES:
        logger.debug(f"Trade blocked: {actual_open}/{config.MAX_OPEN_TRADES} positions open")
        return

    can_trade, reason = risk_mgr.can_open_trade(time.time())
    if not can_trade:
        logger.debug(f"Trade blocked: {reason}")
        return

    sym_info = mr.get_symbol_info(config.SYMBOL)
    if sym_info is None:
        return

    point     = sym_info["point"]
    direction = signal["signal"]

    sl, tp = se.calculate_sl_tp(
        signal      = direction,
        entry_price = tick["ask"] if direction == "BUY" else tick["bid"],
        point       = point,
    )

    trade = te.open_order(
        symbol  = config.SYMBOL,
        signal  = direction,
        lot     = config.INITIAL_LOT,
        sl      = sl,
        tp      = tp,
        comment = f"GS|{signal['score']}",
    )

    if trade is None:
        return

    active_trades[trade["ticket"]] = trade
    risk_mgr.on_trade_opened()
    jl.log_trade_open(trade, analysis, signal["score"], signal.get("breakdown", {}))
    tg.send_trade_open(trade, signal["score"], signal["reason"])


def send_periodic_report(account: dict, positions: list, analysis: dict, tick: dict):
    global last_report_time

    now = datetime.now()
    if last_report_time and (now - last_report_time).total_seconds() < config.REPORT_INTERVAL_MINUTES * 60:
        return

    stats         = jl.get_today_stats()
    risk_status   = risk_mgr.get_status(account["balance"])
    spread_ok     = spread_filter.is_spread_ok(tick)
    spread_status = spread_filter.get_spread_status(tick)

    text = tg.build_report(
        account        = account,
        risk_status    = risk_status,
        analysis       = analysis,
        stats          = stats,
        positions      = positions,
        spread_ok      = spread_ok,
        session_locked = risk_mgr.session_locked,
    )

    jl.log_report({
        **account,
        "today_pnl":      risk_status["today_pnl"],
        "open_trades":    len(positions),
        "closed_trades":  stats["total_trades"],
        "winrate":        stats["winrate"],
        "bias":           analysis.get("m15", {}).get("bias", "NEUTRAL"),
        "spread_status":  spread_status,
        "session_status": "Locked" if risk_mgr.session_locked else "Running",
        "content":        text,
    })

    tg.send_report(text)
    logger.info(f"Report sent | PnL: {risk_status['today_pnl']:+.2f} | WR: {stats['winrate']}%")
    last_report_time = now

    export_summary.run_export()


def main():
    if not acquire_lock():
        sys.exit(1)

    try:
        _run()
    finally:
        release_lock()


def _run():
    logger.info("=" * 60)
    logger.info("Adaptive Multi-Timeframe Gold Scalping Engine Starting")
    logger.info("=" * 60)

    jl.init_db()

    if not mr.connect():
        logger.critical("Cannot connect to MT5 — Exiting")
        sys.exit(1)

    account = mr.get_account_info()
    if account is None:
        logger.critical("Cannot get account info — Exiting")
        mr.disconnect()
        sys.exit(1)

    # ตรวจ PnL วันนี้จาก DB ก่อน reset เพื่อ protect daily limit หลัง restart
    today_closed_pnl = jl.get_today_stats().get("total_profit", 0.0)
    adjusted_balance = account["balance"] - today_closed_pnl
    risk_mgr.reset_session(adjusted_balance)

    tg.send_alert(
        f"🚀 Gold Scalping Engine Started\n"
        f"Balance: {account['balance']:.2f} | "
        f"Target: +{config.DAILY_PROFIT_TARGET:.0f} | "
        f"MaxLoss: -{config.DAILY_MAX_LOSS:.0f}"
    )

    logger.info(f"Account | Balance: {account['balance']:.2f} | Equity: {account['equity']:.2f}")
    iteration = 0

    while running:
        try:
            iteration += 1
            account   = mr.get_account_info()
            tick      = mr.get_tick(config.SYMBOL)
            positions = mr.get_open_positions(config.SYMBOL)

            if account is None or tick is None:
                logger.warning("Missing data — skipping tick")
                time.sleep(2)
                continue

            can_trade = risk_mgr.update(account["balance"], account["equity"])

            check_and_close_positions(positions, account)

            analysis = mtf_analyzer.get_full_analysis(config.SYMBOL)

            send_periodic_report(account, positions, analysis, tick)

            if can_trade:
                try_open_trade(analysis, tick, account, len(positions))
            else:
                if iteration % 60 == 0:
                    logger.info(f"Session locked: {risk_mgr.lock_reason}")

            if iteration % (4 * 3600 // 5) == 0:
                ai_analytics.print_analytics_report(days=7)

            time.sleep(5)

        except Exception as e:
            logger.exception(f"Main loop error: {e}")
            tg.send_alert(f"⚠️ Engine error: {e}")
            time.sleep(30)

    logger.info("Engine stopping...")
    tg.send_alert("🛑 Gold Scalping Engine Stopped")
    mr.disconnect()
    logger.info("Engine stopped cleanly")


if __name__ == "__main__":
    main()
