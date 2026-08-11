"""
Money maths for multi-warehouse splitting.

Two rules the whole system leans on:

1. **Everything is whole Kyats.** MMK has no minor unit and the rest of the app
   already rounds to integers, so allocation happens in ints. No float drift.

2. **Splits must add back up.** If the customer is charged 5,000 Kyats delivery
   and it is shared across 3 warehouses, the three shares must total exactly
   5,000 — not 4,999 (three naive `round()` calls) and not 5,001. That is what
   `allocate_proportional` guarantees, using the largest-remainder method.

Nothing in here touches the database, so it is trivially testable.
"""
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP


def to_kyats(value) -> int:
    """Any numeric (float / Decimal / str) → whole Kyats, half up."""
    return int(Decimal(str(value or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def allocate_proportional(total: int, weights: list[int]) -> list[int]:
    """
    Split `total` across len(weights) buckets in proportion to `weights`,
    in integers, losing nothing.

    Largest-remainder method: give everyone their floor, then hand the leftover
    Kyats one at a time to whoever was robbed most by the flooring.

        allocate_proportional(1000, [500, 300, 200]) -> [500, 300, 200]
        allocate_proportional(100,  [1, 1, 1])       -> [34, 33, 33]
        sum(result) == total, always.

    Zero/empty weights fall back to an even split so a 100%-discounted cart
    still distributes its delivery fee.
    """
    n = len(weights)
    if n == 0:
        return []
    if total == 0:
        return [0] * n

    weight_sum = sum(weights)
    if weight_sum <= 0:                       # no basis to weigh by → even split
        weights = [1] * n
        weight_sum = n

    exact = [Decimal(total) * Decimal(w) / Decimal(weight_sum) for w in weights]
    floors = [int(e) for e in exact]
    leftover = total - sum(floors)

    # biggest fractional part first; index as a stable tie-break
    order = sorted(range(n), key=lambda i: (-(exact[i] - floors[i]), i))
    for i in order[:leftover]:
        floors[i] += 1
    return floors


@dataclass
class SubOrderMoney:
    """The frozen money picture for one warehouse's slice of a parent order."""
    warehouse_id: int
    goods_subtotal: int        # Σ line totals for this warehouse
    discount_share: int        # this warehouse's share of the cart promotion
    delivery_share: int        # this warehouse's share of the single delivery fee
    customer_charged: int      # goods - discount + delivery
    commission_rate: Decimal   # snapshot of the rate that applied at checkout
    commission_amount: int     # platform's cut
    net_payout: int            # what the warehouse earns

    def as_dict(self):
        d = asdict(self)
        d["commission_rate"] = float(self.commission_rate)
        return d


def commission_for(base: int, rate: Decimal) -> int:
    """Platform cut on a base amount, half-up to whole Kyats."""
    return to_kyats(Decimal(base) * Decimal(rate))


def split_order_money(
    groups: list[dict],
    discount_total: int,
    delivery_total: int,
    default_rate: Decimal,
    commission_on_delivery: bool = True,
) -> list[SubOrderMoney]:
    """
    Turn per-warehouse goods totals into complete per-sub-order money.

    groups: [{"warehouse_id": 3, "goods_subtotal": 12000, "rate": Decimal|None}, ...]
            `rate` is the warehouse's override; None → default_rate.
    discount_total / delivery_total: charged ONCE on the parent order.

    The promotion and the delivery fee are both allocated by goods weight, so a
    warehouse that supplied 70% of the basket carries 70% of the discount and
    70% of the shipping.

    Guarantees:
        Σ customer_charged == goods_total - discount_total + delivery_total
        net_payout + commission_amount == customer_charged   (per sub-order)
    """
    weights = [int(g["goods_subtotal"]) for g in groups]
    discounts = allocate_proportional(int(discount_total), weights)
    deliveries = allocate_proportional(int(delivery_total), weights)

    out = []
    for g, disc, ship in zip(groups, discounts, deliveries):
        goods = int(g["goods_subtotal"])
        charged = goods - disc + ship
        rate = Decimal(str(g.get("rate") if g.get("rate") is not None else default_rate))
        # Spec: commission is taken from each sub-order. Flip
        # commission_on_delivery to False to charge it on goods only.
        base = charged if commission_on_delivery else (goods - disc)
        commission = commission_for(base, rate)
        out.append(SubOrderMoney(
            warehouse_id=g["warehouse_id"],
            goods_subtotal=goods,
            discount_share=disc,
            delivery_share=ship,
            customer_charged=charged,
            commission_rate=rate,
            commission_amount=commission,
            net_payout=charged - commission,
        ))
    return out


def assert_balanced(parts: list[SubOrderMoney], goods_total: int,
                    discount_total: int, delivery_total: int) -> None:
    """
    Fail loudly if the split does not reconcile with what the customer pays.
    Called inside the checkout transaction — a mismatch rolls the order back
    rather than quietly creating money.
    """
    expected = int(goods_total) - int(discount_total) + int(delivery_total)
    charged = sum(p.customer_charged for p in parts)
    if charged != expected:
        raise ValueError(
            f"split does not reconcile: sub-orders charge {charged}, "
            f"parent order charges {expected}")
    for p in parts:
        if p.net_payout + p.commission_amount != p.customer_charged:
            raise ValueError(f"sub-order for warehouse {p.warehouse_id} does not balance")
