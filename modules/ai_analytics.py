"""
AI Analytics — วิเคราะห์ข้อมูลย้อนหลัง หา pattern, เสนอ parameter
หมายเหตุ: AI เสนอเท่านั้น ไม่แก้ strategy เอง ต้องให้มนุษย์ approve
"""
import sqlite3
import json
import logging
from datetime import date, timedelta
from contextlib import contextmanager
import config

logger = logging.getLogger(__name__)


@contextmanager
def _conn():
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def analyze_performance(days: int = 7) -> dict:
    """วิเคราะห์ performance ย้อนหลัง N วัน"""
    since = (date.today() - timedelta(days=days)).isoformat()
    with _conn() as con:
        rows = con.execute("""
            SELECT * FROM trades
            WHERE session_date >= ? AND result IS NOT NULL
        """, (since,)).fetchall()

    if not rows:
        return {"message": f"No trades in last {days} days"}

    total  = len(rows)
    wins   = [r for r in rows if r["result"] == "WIN"]
    losses = [r for r in rows if r["result"] == "LOSS"]
    winrate = round(len(wins) / total * 100, 1)

    avg_win  = sum(r["profit"] for r in wins)  / len(wins)  if wins   else 0
    avg_loss = sum(r["profit"] for r in losses) / len(losses) if losses else 0

    # วิเคราะห์ per bias
    bias_stats: dict = {}
    for r in rows:
        b = r["m15_bias"] or "NEUTRAL"
        if b not in bias_stats:
            bias_stats[b] = {"total": 0, "wins": 0}
        bias_stats[b]["total"] += 1
        if r["result"] == "WIN":
            bias_stats[b]["wins"] += 1

    # วิเคราะห์ per confidence level
    score_buckets: dict = {"60-74": {"total": 0, "wins": 0}, "75-89": {"total": 0, "wins": 0}, "90+": {"total": 0, "wins": 0}}
    for r in rows:
        s = r["confidence"] or 0
        if s < 75:
            bucket = "60-74"
        elif s < 90:
            bucket = "75-89"
        else:
            bucket = "90+"
        score_buckets[bucket]["total"] += 1
        if r["result"] == "WIN":
            score_buckets[bucket]["wins"] += 1

    return {
        "period_days": days,
        "total_trades": total,
        "winrate": winrate,
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(abs(avg_win * len(wins)) / abs(avg_loss * len(losses) or 1), 2),
        "bias_performance": {
            k: {"wr": round(v["wins"]/v["total"]*100, 1), "trades": v["total"]}
            for k, v in bias_stats.items()
        },
        "score_performance": {
            k: {"wr": round(v["wins"]/v["total"]*100, 1) if v["total"] else 0, "trades": v["total"]}
            for k, v in score_buckets.items()
        },
    }


def find_best_patterns(days: int = 30) -> list[dict]:
    """หา setup pattern ที่ winrate สูงสุด"""
    since = (date.today() - timedelta(days=days)).isoformat()
    with _conn() as con:
        rows = con.execute("""
            SELECT m15_bias, direction, result, spread, profit
            FROM trades
            WHERE session_date >= ? AND result IS NOT NULL
        """, (since,)).fetchall()

    pattern_stats: dict = {}
    for r in rows:
        key = f"{r['m15_bias']}_{r['direction']}"
        if key not in pattern_stats:
            pattern_stats[key] = {"total": 0, "wins": 0, "profit": 0}
        pattern_stats[key]["total"] += 1
        pattern_stats[key]["profit"] += r["profit"]
        if r["result"] == "WIN":
            pattern_stats[key]["wins"] += 1

    result = []
    for pattern, stats in pattern_stats.items():
        if stats["total"] < 3:
            continue
        wr = round(stats["wins"] / stats["total"] * 100, 1)
        result.append({
            "pattern": pattern,
            "trades": stats["total"],
            "winrate": wr,
            "total_profit": round(stats["profit"], 2),
        })

    return sorted(result, key=lambda x: x["winrate"], reverse=True)


def suggest_parameters(days: int = 14) -> dict:
    """
    เสนอ parameter ใหม่จากการวิเคราะห์
    AI เสนอเท่านั้น — ต้องให้มนุษย์ approve ก่อนใช้
    """
    perf    = analyze_performance(days)
    patterns = find_best_patterns(days)

    suggestions = []

    # ถ้า winrate ต่ำ → แนะนำเพิ่ม threshold
    wr = perf.get("winrate", 0)
    if wr < 55:
        suggestions.append({
            "parameter":   "CONFIDENCE_THRESHOLD",
            "current":     config.CONFIDENCE_THRESHOLD,
            "suggested":   config.CONFIDENCE_THRESHOLD + 5,
            "reason":      f"Winrate {wr}% ต่ำกว่า 55% — เพิ่ม threshold เพื่อกรอง signal ที่ไม่ดี",
            "requires_approval": True,
        })

    # ถ้า avg loss สูงกว่า avg win → ปรับ RR
    avg_win  = abs(perf.get("avg_win", 1))
    avg_loss = abs(perf.get("avg_loss", 1))
    if avg_loss > avg_win * 1.5:
        suggestions.append({
            "parameter":   "SL_MAX_POINTS",
            "current":     config.SL_MAX_POINTS,
            "suggested":   config.SL_MAX_POINTS - 20,
            "reason":      f"Avg loss ({avg_loss:.2f}) สูงกว่า avg win ({avg_win:.2f}) — ลด SL",
            "requires_approval": True,
        })

    # Best performing bias
    bias_perf = perf.get("bias_performance", {})
    best_bias = max(bias_perf.items(), key=lambda x: x[1]["wr"], default=None)
    if best_bias and best_bias[1]["wr"] > 65:
        suggestions.append({
            "observation": f"Best bias: {best_bias[0]} (WR={best_bias[1]['wr']}%)",
            "recommendation": f"พิจารณาเพิ่ม weight ให้ {best_bias[0]} bias",
            "requires_approval": True,
        })

    return {
        "analysis": perf,
        "best_patterns": patterns[:5],
        "suggestions": suggestions,
        "disclaimer": "AI เสนอเท่านั้น — ต้องได้รับ approval จากมนุษย์ก่อนนำไปใช้",
    }


def print_analytics_report(days: int = 7):
    """พิมพ์รายงานสรุปลง log"""
    report = suggest_parameters(days)
    logger.info("=" * 60)
    logger.info(f"AI Analytics Report (Last {days} days)")
    logger.info(f"Performance: {json.dumps(report['analysis'], indent=2, ensure_ascii=False)}")
    logger.info(f"Best Patterns: {json.dumps(report['best_patterns'], indent=2, ensure_ascii=False)}")
    logger.info(f"Suggestions: {json.dumps(report['suggestions'], indent=2, ensure_ascii=False)}")
    logger.info("=" * 60)
    return report
