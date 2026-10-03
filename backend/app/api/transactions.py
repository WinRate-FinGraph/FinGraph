import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from app.api.deps import require_roles
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.account import Account
from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.device import Device
from app.models.merchant import Merchant
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionCreateResponse
from app.services.fraud_scoring import (
    calculate_fraud_score,
    get_alert_severity,
    get_risk_level,
    get_transaction_status,
)
from app.services.graph_sync import sync_transaction_to_graph
from app.ml.inference.tabular_scorer import (
    build_paysim_like_features,
    score_with_active_tabular_model,
)
from app.ml.inference.internal_scorer import (
    build_fingraph_internal_features,
    score_with_internal_adaptive_model,
)

router = APIRouter(prefix="/transactions", tags=["Legacy Transactions"], dependencies=[Depends(require_roles("analyst", "admin"))])


def serialize_transaction(transaction: Transaction):
    return {
        "id": str(transaction.id),
        "transaction_reference": transaction.transaction_reference,
        "sender_account_id": str(transaction.sender_account_id),
        "receiver_account_id": str(transaction.receiver_account_id),
        "device_id": str(transaction.device_id) if transaction.device_id else None,
        "merchant_id": str(transaction.merchant_id) if transaction.merchant_id else None,
        "amount": transaction.amount,
        "currency": transaction.currency,
        "channel": transaction.channel,
        "source_country": transaction.source_country,
        "destination_country": transaction.destination_country,
        "ip_address": transaction.ip_address,
        "status": transaction.status,
        "fraud_score": transaction.fraud_score,
        "risk_level": transaction.risk_level,
        "transaction_time": transaction.transaction_time,
        "created_at": transaction.created_at,
        "sender_account": {
            "id": str(transaction.sender_account.id),
            "account_number": transaction.sender_account.account_number,
            "holder_name": transaction.sender_account.holder_name,
            "risk_level": transaction.sender_account.risk_level,
        }
        if transaction.sender_account
        else None,
        "receiver_account": {
            "id": str(transaction.receiver_account.id),
            "account_number": transaction.receiver_account.account_number,
            "holder_name": transaction.receiver_account.holder_name,
            "risk_level": transaction.receiver_account.risk_level,
        }
        if transaction.receiver_account
        else None,
        "device": {
            "id": str(transaction.device.id),
            "device_fingerprint": transaction.device.device_fingerprint,
            "device_type": transaction.device.device_type,
            "os": transaction.device.os,
            "browser": transaction.device.browser,
            "ip_address": transaction.device.ip_address,
            "risk_level": transaction.device.risk_level,
            "is_blacklisted": transaction.device.is_blacklisted,
        }
        if transaction.device
        else None,
        "merchant": {
            "id": str(transaction.merchant.id),
            "name": transaction.merchant.name,
            "category": transaction.merchant.category,
            "country_code": transaction.merchant.country_code,
            "risk_level": transaction.merchant.risk_level,
            "is_blacklisted": transaction.merchant.is_blacklisted,
        }
        if transaction.merchant
        else None,
    }


@router.get("")
def get_transactions(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    risk_level: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    query = db.query(Transaction)

    if risk_level:
        query = query.filter(Transaction.risk_level == risk_level)

    if status:
        query = query.filter(Transaction.status == status)

    total = query.count()

    transactions = (
        query.order_by(Transaction.transaction_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [serialize_transaction(transaction) for transaction in transactions],
    }


@router.post("", response_model=TransactionCreateResponse)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
):
    sender_account = (
        db.query(Account).filter(Account.id == payload.sender_account_id).first()
    )

    if not sender_account:
        raise HTTPException(status_code=404, detail="Sender account not found")

    receiver_account = (
        db.query(Account).filter(Account.id == payload.receiver_account_id).first()
    )

    if not receiver_account:
        raise HTTPException(status_code=404, detail="Receiver account not found")

    if sender_account.id == receiver_account.id:
        raise HTTPException(
            status_code=400,
            detail="Sender and receiver account cannot be the same",
        )

    device = None
    if payload.device_id:
        device = db.query(Device).filter(Device.id == payload.device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

    merchant = None
    if payload.merchant_id:
        merchant = db.query(Merchant).filter(Merchant.id == payload.merchant_id).first()
        if not merchant:
            raise HTTPException(status_code=404, detail="Merchant not found")

    rule_score, reasons = calculate_fraud_score(
        amount=payload.amount,
        source_country=payload.source_country,
        destination_country=payload.destination_country,
        sender_account=sender_account,
        receiver_account=receiver_account,
        device=device,
        merchant=merchant,
    )

    tabular_features = build_paysim_like_features(
        amount=payload.amount,
        channel=payload.channel,
        source_country=payload.source_country,
        destination_country=payload.destination_country,
        sender_risk_level=sender_account.risk_level,
        receiver_risk_level=receiver_account.risk_level,
        device_risk_level=device.risk_level if device else "low",
        device_is_blacklisted=device.is_blacklisted if device else False,
        merchant_risk_level=merchant.risk_level if merchant else "low",
        merchant_is_blacklisted=merchant.is_blacklisted if merchant else False,
    )

    tabular_result = score_with_active_tabular_model(tabular_features)

    preliminary_status = get_transaction_status(rule_score)

    internal_features = build_fingraph_internal_features(
        amount=payload.amount,
        currency=payload.currency,
        channel=payload.channel,
        source_country=payload.source_country,
        destination_country=payload.destination_country,
        rule_fraud_score=rule_score,
        transaction_status=preliminary_status,
        sender_risk_level=sender_account.risk_level,
        receiver_risk_level=receiver_account.risk_level,
        device_risk_level=device.risk_level if device else "low",
        device_is_blacklisted=device.is_blacklisted if device else False,
        merchant_risk_level=merchant.risk_level if merchant else "low",
        merchant_is_blacklisted=merchant.is_blacklisted if merchant else False,
    )

    internal_result = score_with_internal_adaptive_model(internal_features)

    score_candidates = [rule_score]
    weighted_parts = [rule_score * 0.50]

    if tabular_result.used_model:
        score_candidates.append(tabular_result.tabular_ml_score)
        weighted_parts.append(tabular_result.tabular_ml_score * 0.30)
        reasons.append(
            f"PaySim XGBoost model contributed score {tabular_result.tabular_ml_score}"
        )
    else:
        reasons.append("No active PaySim model available")

    if internal_result.used_model:
        score_candidates.append(internal_result.internal_ml_score)
        weighted_parts.append(internal_result.internal_ml_score * 0.20)
        reasons.append(
            f"FinGraph internal adaptive model contributed score {internal_result.internal_ml_score}"
        )
    else:
        reasons.append("No FinGraph internal adaptive model available")

    blended_score = round(sum(weighted_parts), 2)

    fraud_score = round(max(rule_score, blended_score, *score_candidates), 2)

    reasons.append(
        f"Final score selected using ensemble guard: max(rule={rule_score}, blend={blended_score})"
    )

    risk_level = get_risk_level(fraud_score)
    status = get_transaction_status(fraud_score)

    transaction = Transaction(
        transaction_reference=f"TRX-{uuid.uuid4().hex[:12].upper()}",
        sender_account_id=payload.sender_account_id,
        receiver_account_id=payload.receiver_account_id,
        device_id=payload.device_id,
        merchant_id=payload.merchant_id,
        amount=payload.amount,
        currency=payload.currency,
        channel=payload.channel,
        source_country=payload.source_country,
        destination_country=payload.destination_country,
        ip_address=payload.ip_address or (device.ip_address if device else None),
        status=status,
        fraud_score=fraud_score,
        risk_level=risk_level,
    )

    db.add(transaction)
    db.flush()

    alert_created = False

    if fraud_score >= 0.50:
        alert = Alert(
            transaction_id=transaction.id,
            alert_type="fraud_risk",
            severity=get_alert_severity(fraud_score),
            risk_score=fraud_score,
            reason="; ".join(reasons),
            status="open",
            assigned_to=None,
        )
        db.add(alert)
        alert_created = True

    audit_log = AuditLog(
        actor="system",
        actor_role="system",
        action="create_transaction",
        entity_type="transaction",
        entity_id=str(transaction.id),
        description=(
            f"Created transaction {transaction.transaction_reference} "
            f"with fraud score {fraud_score} and risk level {risk_level}."
        ),
    )
    db.add(audit_log)

    db.commit()
    db.refresh(transaction)
    try:
        sync_transaction_to_graph(transaction)
    except Exception as exc:
        print(f"[Neo4j Sync Warning] {exc}")

    return TransactionCreateResponse(
        message="Transaction created and scored successfully",
        transaction_id=str(transaction.id),
        transaction_reference=transaction.transaction_reference,
        fraud_score=transaction.fraud_score,
        risk_level=transaction.risk_level,
        status=transaction.status,
        alert_created=alert_created,

        ml_model_used=tabular_result.used_model or internal_result.used_model,
        ml_score=tabular_result.tabular_ml_score if tabular_result.used_model else None,

        tabular_ml_model_used=tabular_result.used_model,
        tabular_ml_score=tabular_result.tabular_ml_score if tabular_result.used_model else None,
        tabular_model_version=tabular_result.model_version,

        internal_ml_model_used=internal_result.used_model,
        internal_ml_score=internal_result.internal_ml_score if internal_result.used_model else None,
        internal_model_version=internal_result.model_version,

        ensemble_mode="risk_aware_max_guard",
    )


@router.get("/demo/options")
def get_demo_transaction_options(db: Session = Depends(get_db)):
    accounts = db.query(Account).limit(10).all()
    devices = db.query(Device).limit(10).all()
    merchants = db.query(Merchant).limit(10).all()

    return {
        "accounts": [
            {
                "id": str(account.id),
                "account_number": account.account_number,
                "holder_name": account.holder_name,
                "risk_level": account.risk_level,
            }
            for account in accounts
        ],
        "devices": [
            {
                "id": str(device.id),
                "device_fingerprint": device.device_fingerprint,
                "risk_level": device.risk_level,
                "is_blacklisted": device.is_blacklisted,
            }
            for device in devices
        ],
        "merchants": [
            {
                "id": str(merchant.id),
                "name": merchant.name,
                "category": merchant.category,
                "risk_level": merchant.risk_level,
                "is_blacklisted": merchant.is_blacklisted,
            }
            for merchant in merchants
        ],
    }


@router.get("/{transaction_id}")
def get_transaction_detail(
    transaction_id: UUID,
    db: Session = Depends(get_db),
):
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return serialize_transaction(transaction)
