import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, merchant_scope_id
from app.core.security import pseudonymize_payer
from app.db.session import get_db
from app.models.qris import Order, Outlet, PaymentEvent
from app.models.user import User
from app.schemas.qris import OrderCreate, OrderStatusUpdate, PaymentMatchRequest
from app.services.audit import add_audit
from app.services.qris_serializers import order_dict, payment_dict
from app.api.pagination import page_response


router = APIRouter(prefix="/orders", tags=["QRIS Orders"])


def scoped_order(db: Session, user: User, order_id) -> Order:
    query = db.query(Order).filter(Order.id == order_id)
    scope = merchant_scope_id(user, db)
    if scope:
        query = query.filter(Order.merchant_id == scope)
    order = query.first()
    if not order:
        raise HTTPException(status_code=404, detail="Pesanan tidak ditemukan")
    return order


@router.get("")
def list_orders(
    limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0),
    status: str | None = None, merchant_id: uuid.UUID | None = None,
    outlet_id: uuid.UUID | None = None, search: str | None = Query(default=None, max_length=120),
    ordering: str = Query(default="newest", pattern="^(newest|oldest|amount_desc)$"),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    query = db.query(Order)
    scope = merchant_scope_id(user, db)
    if scope:
        query = query.filter(Order.merchant_id == scope)
    elif merchant_id:
        query = query.filter(Order.merchant_id == merchant_id)
    if status:
        query = query.filter(Order.status == status)
    if outlet_id:
        query = query.filter(Order.outlet_id == outlet_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(Order.order_reference.ilike(pattern) | Order.description.ilike(pattern))
    total = query.count()
    order_columns = {
        "newest": (Order.created_at.desc(), Order.id.desc()),
        "oldest": (Order.created_at.asc(), Order.id.asc()),
        "amount_desc": (Order.expected_amount.desc(), Order.created_at.desc(), Order.id.desc()),
    }[ordering]
    items = query.order_by(*order_columns).offset(offset).limit(limit).all()
    return page_response(total=total, limit=limit, offset=offset, items=[order_dict(item) for item in items])


@router.post("", status_code=201)
def create_order(payload: OrderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    merchant_id = merchant_scope_id(user, db)
    if not merchant_id:
        raise HTTPException(status_code=403, detail="Pesanan dibuat melalui akun merchant")
    outlet = db.query(Outlet).filter(Outlet.id == payload.outlet_id, Outlet.merchant_id == merchant_id).first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet bukan milik merchant ini")
    data = payload.model_dump()
    customer_ref = data.pop("customer_reference", None)
    order = Order(
        order_reference=f"ORD-{uuid.uuid4().hex[:12].upper()}", merchant_id=merchant_id,
        customer_reference=pseudonymize_payer(customer_ref) if customer_ref else None,
        status="awaiting_payment", **data,
    )
    db.add(order); db.flush()
    add_audit(db, action="create_order", entity_type="order", entity_id=str(order.id), description=f"Pesanan {order.order_reference} dibuat.", user=user, merchant_id=merchant_id)
    db.commit(); db.refresh(order)
    return order_dict(order)


@router.get("/{order_id}")
def get_order(order_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = scoped_order(db, user, order_id)
    result = order_dict(order)
    result["payments"] = [payment_dict(item) for item in order.payments]
    return result


@router.patch("/{order_id}/status")
def update_order_status(order_id: uuid.UUID, payload: OrderStatusUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = scoped_order(db, user, order_id)
    # Payment-derived states are controlled exclusively by a verified provider
    # callback. Allowing a user to set them would bypass payment verification.
    if payload.status in {"paid", "held"}:
        raise HTTPException(
            status_code=409,
            detail="Status paid/held hanya dapat ditetapkan oleh proses verifikasi pembayaran",
        )
    if payload.status == "completed" and order.status != "paid":
        raise HTTPException(
            status_code=409,
            detail="Pesanan hanya dapat diselesaikan setelah pembayaran terverifikasi",
        )
    old = order.status
    order.status = payload.status
    add_audit(db, action="update_order_status", entity_type="order", entity_id=str(order.id), description=f"Status pesanan berubah dari {old} menjadi {payload.status}.", user=user, merchant_id=order.merchant_id)
    db.commit(); db.refresh(order)
    return order_dict(order)


@router.post("/{order_id}/match-payment")
def match_payment(order_id: uuid.UUID, payment_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = scoped_order(db, user, order_id)
    query = db.query(PaymentEvent).filter(PaymentEvent.id == payment_id)
    if user.role == "merchant":
        query = query.filter(PaymentEvent.merchant_id == order.merchant_id)
    payment = query.first()
    if not payment:
        raise HTTPException(status_code=404, detail="Pembayaran tidak ditemukan")
    if payment.order_id and payment.order_id != order.id:
        raise HTTPException(status_code=409, detail="Pembayaran sudah terhubung dengan pesanan lain")
    payment.order_id = order.id
    payment.expected_amount = order.expected_amount
    if (
        payment.payment_status == "success"
        and payment.callback_received
        and payment.signature_valid
        and payment.risk_level == "low"
        and float(payment.amount) == float(order.expected_amount)
    ):
        order.status = "paid"
    add_audit(db, action="match_payment_to_order", entity_type="payment_event", entity_id=str(payment.id), description=f"Pembayaran dicocokkan ke {order.order_reference}.", user=user, merchant_id=order.merchant_id)
    db.commit(); db.refresh(payment)
    return {"order": order_dict(order), "payment": payment_dict(payment, detailed=True)}
