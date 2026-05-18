"""
Export Summary — ดึงข้อมูลจาก trades.db แล้ว push summary.json ขึ้น GitHub
เรียกจาก main.py ทุก 15 นาที
"""
import json
import sqlite3
import subprocess
import logging
import os
from datetime import date, datetime
import config

logger = logging.getLogger(__name__)

PROJ = r"C:\Users\nattawadee\GoldScalpingEngine"
SUMMARY_PATH = os.path.join(PROJ, "summary.json")


def _read_db() -> dict:
    today = date.today().isoformat()
    try:
        con = sqlite3.connect(config.DB_PATH)
        con.row_factory = sqlite3.Row

        # stats วันนี้
        row = con.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END) as wins,
                   SUM(profit) as pnl,
                   AVG(CASE WHEN result='WIN' THEN profit ELSE NULL END) as avg_win,
                   AVG(CASE WHEN result='LOSS' THEN profit ELSE NULL END) as avg_loss
            FROM trades WHERE session_date=? AND result IS NOT NULL
        """, (today,)).fetchone()

        open_row = con.execute(
            "SELECT COUNT(*) as c FROM trades WHERE exit_price IS NULL"
        ).fetchone()

        # report ล่าสุด
        rpt = con.execute("""
            SELECT balance, equity, today_pnl, bias, spread_status, session_status, report_time
            FROM reports ORDER BY id DESC LIMIT 1
        """).fetchone()

        # trades ล่าสุด 10 ไม้
        recent = con.execute("""
            SELECT direction, entry_price, exit_price, profit, result, entry_time, confidence
            FROM trades WHERE session_date=?
            ORDER BY id DESC LIMIT 10
        """, (today,)).fetchall()

        con.close()

        total = row["total"] or 0
        wins  = row["wins"]  or 0
        pnl   = row["pnl"]   or 0.0

        return {
            "updated_at": datetime.now().isoformat(),
            "date": today,
            "account": {
                "balance":  rpt["balance"]   if rpt else 0,
                "equity":   rpt["equity"]    if rpt else 0,
                "today_pnl": rpt["today_pnl"] if rpt else 0,
                "session_status": rpt["session_status"] if rpt else "Unknown",
            },
            "stats": {
                "total_trades": total,
                "wins":    wins,
                "losses":  total - wins,
                "winrate": round(wins / total * 100, 1) if total > 0 else 0.0,
                "pnl":     round(pnl, 2),
                "avg_win":  round(row["avg_win"]  or 0, 2),
                "avg_loss": round(row["avg_loss"] or 0, 2),
                "open_trades": open_row["c"],
            },
            "market": {
                "bias":          rpt["bias"]          if rpt else "NEUTRAL",
                "spread_status": rpt["spread_status"] if rpt else "N/A",
                "last_report":   rpt["report_time"]   if rpt else None,
            },
            "recent_trades": [
                {
                    "dir":        r["direction"],
                    "entry":      r["entry_price"],
                    "exit":       r["exit_price"],
                    "profit":     r["profit"],
                    "result":     r["result"],
                    "time":       r["entry_time"],
                    "confidence": r["confidence"],
                }
                for r in recent
            ],
        }
    except Exception as e:
        logger.error(f"export read_db error: {e}")
        return {"error": str(e), "updated_at": datetime.now().isoformat()}


def _git_push(data: dict):
    try:
        with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        env = os.environ.copy()
        env["PATH"] = (
            r"C:\Program Files\Git\cmd;" +
            r"C:\Program Files\Git\bin;" +
            env.get("PATH", "")
        )

        def run(cmd):
            return subprocess.run(
                cmd, cwd=PROJ, capture_output=True, text=True, env=env
            )

        run(["git", "add", "summary.json"])
        msg = f"update: {datetime.now().strftime('%Y-%m-%d %H:%M')} | PnL:{data.get('account',{}).get('today_pnl',0):+.0f}"
        result = run(["git", "commit", "-m", msg])
        if "nothing to commit" in result.stdout:
            return

        push = run(["git", "push", "origin", "main", "--force"])
        if push.returncode == 0:
            logger.info(f"Summary pushed to GitHub: {msg}")
        else:
            logger.warning(f"Git push failed: {push.stderr[:200]}")

    except Exception as e:
        logger.error(f"export git_push error: {e}")


def run_export():
    data = _read_db()
    _git_push(data)
