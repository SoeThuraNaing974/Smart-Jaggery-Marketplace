"""Per-order messaging between a customer and their assigned warehouse."""
from flask import Blueprint, request, jsonify, g

from db import db
from models import Order, OrderMessage
from auth import token_required

bp = Blueprint("messages", __name__, url_prefix="/api")


def _accessible_order(order_id):
    """Return the order if the current user may view/message it, else None."""
    order = db.session.get(Order, order_id)
    if not order:
        return None
    u = g.current_user
    if u.role == "admin":
        return order
    if u.role == "customer" and order.customer_id == u.id:
        return order
    if u.role == "warehouse" and order.assigned_warehouse_id == u.warehouse_id:
        return order
    return None


@bp.get("/orders/<int:order_id>/messages")
@token_required
def list_messages(order_id):
    order = _accessible_order(order_id)
    if not order:
        return jsonify({"error": "order not found or not accessible"}), 404
    msgs = (OrderMessage.query.filter_by(order_id=order_id)
            .order_by(OrderMessage.created_at.asc()).all())
    return jsonify([m.to_dict() for m in msgs])


@bp.post("/orders/<int:order_id>/messages")
@token_required
def post_message(order_id):
    order = _accessible_order(order_id)
    if not order:
        return jsonify({"error": "order not found or not accessible"}), 404
    text = (request.get_json(silent=True) or {}).get("message", "").strip()
    if not text:
        return jsonify({"error": "message cannot be empty"}), 400

    msg = OrderMessage(order_id=order_id, sender_id=g.current_user.id,
                       sender_role=g.current_user.role, message=text)
    db.session.add(msg)
    db.session.commit()
    return jsonify({"message": "sent", "data": msg.to_dict()}), 201
