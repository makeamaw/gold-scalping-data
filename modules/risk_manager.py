"""
Risk Manager — Daily PnL tracking, session lock, equity protection
"""
import logging
from datetime import date
import config

logger = logging.getLogger(__name__)


class RiskManager:
    def __init__(self):
        self.session_date: date = date.today()
        self.session_locked: bool = False
        self.lock_reason: str = ""

        self.starting_balance_today: float = 0.0
        self.peak_profit_today: float = 0.0    # สูงสุดที่กำไรไปถึงวันนี้
        self._equity_protect_triggered: bool = False

        self.last_trade_close_time = None   # สำหรับ cooldown
        self.open_trade_count: int = 0

    def reset_session(self, current_balance: float):
        """เรียกเมื่อขึ้นวันใหม่"""
        self.session_date = date.today()
        self.session_locked = False
        self.lock_reason = ""
        self.starting_balance_today = current_balance
        self.peak_profit_today = 0.0
        self._equity_protect_triggered = False
        logger.info(f"Session reset | Start balance: {current_balance:.2f}")

    def update(self, balance: float, equity: float) -> bool:
        """
        อัปเดตสถานะ risk ทุก tick
        Returns True ถ้ายังเทรดได้
        """
        # ตรวจสอบวันใหม่
        if date.today() != self.session_date:
            self.reset_session(balance)

        if self.session_locked:
            return False

        today_pnl = balance - self.starting_balance_today
        equity_pnl = equity - self.starting_balance_today

        # อัปเดต peak profit
        if today_pnl > self.peak_profit_today:
            self.peak_profit_today = today_pnl

        # Daily max loss
        if today_pnl <= -config.DAILY_MAX_LOSS:
            self._lock(f"Daily max loss reached: {today_pnl:.2f}")
            return False

        # Daily profit target
        if today_pnl >= config.DAILY_PROFIT_TARGET:
            self._lock(f"Daily profit target reached: {today_pnl:.2f}")
            return False

        # Equity protection
        if (
            self.peak_profit_today >= config.EQUITY_PROTECT_PEAK_TRIGGER
            and equity_pnl < config.EQUITY_PROTECT_THRESHOLD
            and not self._equity_protect_triggered
        ):
            self._equity_protect_triggered = True
            self._lock(
                f"Equity protection: peak={self.peak_profit_today:.2f}, "
                f"current={equity_pnl:.2f}"
            )
            return False

        return True

    def _lock(self, reason: str):
        self.session_locked = True
        self.lock_reason = reason
        logger.warning(f"Session LOCKED: {reason}")

    def can_open_trade(self, current_time) -> tuple[bool, str]:
        """ตรวจสอบว่าสามารถเปิดออเดอร์ใหม่ได้ไหม"""
        if self.session_locked:
            return False, self.lock_reason

        if self.open_trade_count >= config.MAX_OPEN_TRADES:
            return False, f"Max open trades ({config.MAX_OPEN_TRADES}) reached"

        # Cooldown
        if self.last_trade_close_time is not None:
            import time
            elapsed = time.time() - self.last_trade_close_time
            if elapsed < config.COOLDOWN_SECONDS:
                remaining = int(config.COOLDOWN_SECONDS - elapsed)
                return False, f"Cooldown: {remaining}s remaining"

        return True, "OK"

    def on_trade_opened(self):
        self.open_trade_count += 1

    def on_trade_closed(self):
        import time
        self.open_trade_count = max(0, self.open_trade_count - 1)
        self.last_trade_close_time = time.time()

    def get_status(self, balance: float) -> dict:
        today_pnl = balance - self.starting_balance_today
        return {
            "locked": self.session_locked,
            "lock_reason": self.lock_reason,
            "today_pnl": round(today_pnl, 2),
            "peak_profit": round(self.peak_profit_today, 2),
            "open_trades": self.open_trade_count,
            "progress_to_target": f"{today_pnl:.0f}/{config.DAILY_PROFIT_TARGET:.0f}",
        }
