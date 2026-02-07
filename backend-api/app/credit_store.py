from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.db import session_scope
from app.models import CreditBalanceModel, CreditLedgerEntryModel
from app.schemas import CreditBalanceResponse, CreditConsumeRequest, CreditGrantRequest, CreditOperationResponse


def get_balance(user_id: str) -> CreditBalanceResponse:
    with session_scope() as session:
        balance_model = session.get(CreditBalanceModel, user_id)
        if not balance_model:
            return CreditBalanceResponse(user_id=user_id, balance=0)
        return CreditBalanceResponse(user_id=user_id, balance=balance_model.balance)


def consume_credits(payload: CreditConsumeRequest) -> CreditOperationResponse:
    with session_scope() as session:
        if payload.idempotency_key:
            existing = _find_ledger_by_idempotency(session, payload.idempotency_key)
            if existing:
                balance_model = session.get(CreditBalanceModel, payload.user_id)
                return CreditOperationResponse(
                    user_id=payload.user_id,
                    balance=balance_model.balance if balance_model else 0,
                    applied=False,
                )

        balance_model = session.get(CreditBalanceModel, payload.user_id)
        if not balance_model:
            balance_model = CreditBalanceModel(user_id=payload.user_id, balance=0)
            session.add(balance_model)

        if balance_model.balance < payload.amount:
            raise ValueError("insufficient_credits")

        balance_model.balance -= payload.amount
        balance_model.updated_at = datetime.utcnow()

        session.add(
            CreditLedgerEntryModel(
                user_id=payload.user_id,
                delta=-payload.amount,
                reason=payload.reason,
                idempotency_key=payload.idempotency_key,
                metadata_json=payload.metadata,
            )
        )

        return CreditOperationResponse(
            user_id=payload.user_id,
            balance=balance_model.balance,
            applied=True,
        )


def grant_credits(payload: CreditGrantRequest) -> CreditOperationResponse:
    with session_scope() as session:
        if payload.idempotency_key:
            existing = _find_ledger_by_idempotency(session, payload.idempotency_key)
            if existing:
                balance_model = session.get(CreditBalanceModel, payload.user_id)
                return CreditOperationResponse(
                    user_id=payload.user_id,
                    balance=balance_model.balance if balance_model else 0,
                    applied=False,
                )

        balance_model = session.get(CreditBalanceModel, payload.user_id)
        if not balance_model:
            balance_model = CreditBalanceModel(user_id=payload.user_id, balance=0)
            session.add(balance_model)

        balance_model.balance += payload.amount
        balance_model.updated_at = datetime.utcnow()

        session.add(
            CreditLedgerEntryModel(
                user_id=payload.user_id,
                delta=payload.amount,
                reason=payload.reason,
                idempotency_key=payload.idempotency_key,
                metadata_json=payload.metadata,
            )
        )

        return CreditOperationResponse(
            user_id=payload.user_id,
            balance=balance_model.balance,
            applied=True,
        )


def _find_ledger_by_idempotency(session, idempotency_key: str) -> CreditLedgerEntryModel | None:
    stmt = select(CreditLedgerEntryModel).where(CreditLedgerEntryModel.idempotency_key == idempotency_key)
    return session.execute(stmt).scalar_one_or_none()
