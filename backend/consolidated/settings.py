"""
Tunable policy for the consolidated flow — commission, SLAs, refund rules.

Read from environment variables so the platform owner can change the commission
without a deploy, with sane defaults for local development. Kept in one place so
the service layer never hard-codes a business rule.
"""
import os
from decimal import Decimal

from config import Config


def _env_decimal(name, default):
    try:
        return Decimal(str(os.getenv(name, default)))
    except Exception:                        # noqa: BLE001 — bad env must not crash boot
        return Decimal(str(default))


def _env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return int(default)


def _env_bool(name, default):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class _Settings:
    # ---- money ----------------------------------------------------------
    def commission_rate(self) -> Decimal:
        """Platform commission as a fraction: 0.05 = 5%. Per-warehouse overrides
        live in warehouses.commission_rate and win over this default."""
        return _env_decimal("PLATFORM_COMMISSION_RATE", "0.05")

    def commission_on_delivery(self) -> bool:
        """True → commission is charged on goods + the delivery share (the spec's
        'commission from each sub-order'). False → goods only."""
        return _env_bool("COMMISSION_ON_DELIVERY", True)

    def default_delivery_fee(self) -> int:
        return int(round(float(Config.DEFAULT_DELIVERY_FEE)))

    def refund_delivery_share_on_partial(self) -> bool:
        """When one warehouse cancels, does the customer get that warehouse's
        share of the delivery fee back? Default yes — they received less."""
        return _env_bool("REFUND_DELIVERY_SHARE_ON_PARTIAL", True)

    # ---- preparation SLA / rider delay strategy -------------------------
    def prep_window_hours(self) -> int:
        """How long a warehouse has to reach 'Ready for Pickup' after payment."""
        return _env_int("PREP_WINDOW_HOURS", 4)

    def partial_dispatch_after_minutes(self) -> int:
        """Grace past the deadline before the rider leaves with what is ready."""
        return _env_int("PARTIAL_DISPATCH_AFTER_MINUTES", 30)

    def auto_cancel_after_minutes(self) -> int:
        """Hard limit: past this, the late sub-order is cancelled and refunded."""
        return _env_int("AUTO_CANCEL_AFTER_MINUTES", 180)

    # ---- delivery proof --------------------------------------------------
    def require_delivery_otp(self) -> bool:
        return _env_bool("REQUIRE_DELIVERY_OTP", True)

    def as_dict(self):
        return {
            "commission_rate": float(self.commission_rate()),
            "commission_on_delivery": self.commission_on_delivery(),
            "default_delivery_fee": self.default_delivery_fee(),
            "refund_delivery_share_on_partial": self.refund_delivery_share_on_partial(),
            "prep_window_hours": self.prep_window_hours(),
            "partial_dispatch_after_minutes": self.partial_dispatch_after_minutes(),
            "auto_cancel_after_minutes": self.auto_cancel_after_minutes(),
            "require_delivery_otp": self.require_delivery_otp(),
        }


settings = _Settings()
