"""Business logic shared across routes."""
from datetime import date

from models import Promotion, PriceAlert


def trigger_price_alerts(batch):
    """Mark matching unnotified alerts as notified when a batch's price drops to
    or below a customer's desired price. Returns the number of alerts fired.
    Caller commits."""
    alerts = PriceAlert.query.filter(
        PriceAlert.batch_id == batch.id,
        PriceAlert.is_notified.is_(False),
        PriceAlert.desired_price >= batch.price_per_kg,
    ).all()
    for a in alerts:
        a.is_notified = True
    return len(alerts)


def best_promotion_for(total_qty, on_date=None):
    """Return the active promotion giving the biggest discount for `total_qty`.

    A promotion auto-applies if the order meets its min_qty and today is within
    [start_date, end_date]. If several qualify, pick the highest discount_percent.
    Returns None if nothing qualifies.
    """
    on_date = on_date or date.today()
    candidates = Promotion.query.filter(
        Promotion.is_active.is_(True),
        Promotion.start_date <= on_date,
        Promotion.end_date >= on_date,
        Promotion.min_qty <= total_qty,
    ).all()
    if not candidates:
        return None
    return max(candidates, key=lambda p: float(p.discount_percent))


def price_order(line_items, total_qty):
    """line_items: list of dicts with 'line_total'. Returns (subtotal, discount, total, promo)."""
    subtotal = sum(float(li["line_total"]) for li in line_items)
    promo = best_promotion_for(total_qty)
    discount = 0.0
    if promo:
        discount = round(subtotal * float(promo.discount_percent) / 100.0)
    total = round(subtotal - discount)
    return round(subtotal), discount, total, promo
