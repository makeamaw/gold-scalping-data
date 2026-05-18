"""
Journal Logger — SQLite trade journal บันทึกทุกออเดอร์
"""
import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager
import config

logger = logging.getLogger(__name__)


@contextmanager
def _conn():
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket         INTEGER UNIQUE,
                symbol         TEXT,
                direction      TEXT,
                lot            REAL,
                entry_price    REAL,
                exit_price     REAL,
                sl             REAL,
                tp             REAL,
                rr_ratio       REAL,
                spread         INTEGER,
                volatility     REAL,
                entry_time     TEXT,
                exit_time      TEXT,
                setup_type     TEXT,
                confidence     INTEGER,
                score_breakdown TEXT,
                m15_bias       TEXT,
                profit         REAL,
                result         TEXT,
                session_date   TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                report_time TEXT,
                balance     REAL,
                equity      REAL,
                today_pnl   REAL,
                open_trades INTEGER,
                closed_trades INTEGER,
                winrate     REAL,
                bias        TEXT,
                spread_status TEXT,
                session_status TEXT,
                content     TEXT
            )
        """)
    logger.info("Database initialized")


def log_trade_open(trade: dict, analysis: dict, score: int, score_breakdown: dict):
    """บันทึกออเดอร์ที่เปิดใหม่"""
    import json
    m5 = analysis.get("m5", {})
    rsi = m5.get("rsi", 0) or 0
    volatility = rsi  # ใช้ RSI เป็น proxy volatility ชั่วคราว

    sl = trade.get("sl", 0)
    tp = trade.get("tp", 0)
    entry = trade.get("entry_price", 0)
    direction = trade.get("type", "BUY")

    if direction == "BUY":
        risk = entry - sl
        reward = tp - entry
    else:
        risk = sl - entry
        reward = entry - tp

    rr = round(reward / risk, 2) if risk > 0 else 0

    with _conn() as con:
        con.execute("""
            INSERT OR IGNORE INTO trades
            (ticket, symbol, direction, lot, entry_price, sl, tp, rr_ratio,
             spread, volatility, entry_time, setup_type, confidence,
             score_breakdown, m15_bias, session_date)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            trade.get("ticket"),
            trade.get("symbol"),
            direction,
            trade.get("lot"),
            entry,
            sl,
            tp,
            rr,
            trade.get("spread", 0),
            round(volatility, 1),
            trade.get("open_time", datetime.now()).isoformat(),
            "MTF_Scalp",
            score,
            json.dumps(score_breakdown),
            analysis.get("m15", {}).get("bias", "NEUTRAL"),
            datetime.now().date().isoformat(),
        ))


def log_trade_close(ticket: int, exit_price: float, profit: float, exit_time: datetime):
    """อัปเดตออเดอร์เมื่อปิด"""
    result = "WIN" if profit > 0 else "LOSS"
    with _conn() as con:
        con.execute("""
            UPDATE trades SET
                exit_price = ?,
                profit     = ?,
                result     = ?,
                exit_time  = ?
            WHERE ticket = ?
        """, (exit_price, profit, result, exit_time.isoformat(), ticket))


def log_report(report: dict):
    with _conn() as con:
        con.execute("""
            INSERT INTO reports
            (report_time, balance, equity, today_pnl, open_trades,
             closed_trades, winrate, bias, spread_status, session_status, content)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            datetime.now().isoformat(),
            report.get("balance", 0),
            report.get("equity", 0),
            report.get("today_pnl", 0),
            report.get("open_trades", 0),
            report.get("closed_trades", 0),
            report.get("winrate", 0),
            report.get("bias", "NEUTRAL"),
            report.get("spread_status", "N/A"),
            report.get("session_status", "Running"),
            report.get("content", ""),
        ))


def get_today_stats() -> dict:
    from datetime import date
    today = date.today().isoformat()
    with _conn() as con:
        row = con.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) as wins,
                SUM(profit) as total_profit,
                AVG(CASE WHEN result='WIN' THEN profit ELSE NULL END) as avg_win,
                AVG(CASE WHEN result='LOSS' THEN profit ELSE NULL END) as avg_loss
            FROM trades
            WHERE session_date = ? AND result IS NOT NULL
        """, (today,)).fetchone()

    total  = row["total"] or 0
    wins   = row["wins"] or 0
    winrate = round(wins / total * 100, 1) if total > 0 else 0.0

    return {
        "total_trades": total,
        "wins": wins,
        "losses": total - wins,
        "winrate": winrate,
        "total_profit": round(row["total_profit"] or 0, 2),
        "avg_win": round(row["avg_win"] or 0, 2),
        "avg_loss": round(row["avg_loss"] or 0, 2),
    }


def get_open_tickets() -> list[int]:
    with _conn() as con:
        rows = con.execute(
            "SELECT ticket FROM trades WHERE exit_price IS NULL"
        ).fetchall()
    return [r["ticket"] for r in rows]
