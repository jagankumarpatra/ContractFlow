from datetime import datetime, timedelta
from app.workers.celery_app import celery_app
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_contract_task(self, contract_id: str):
    """
    Async task: run AI analysis on a contract and save results.
    """
    try:
        from app.db.base import SessionLocal
        from app.models.contract import Contract
        from app.services.ai_service import analyze_contract

        db = SessionLocal()
        try:
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            if not contract:
                logger.error(f"Contract {contract_id} not found")
                return {"error": "Contract not found"}

            text = contract.contract_text or f"Contract: {contract.title}"
            analysis = analyze_contract(text, contract.title)

            contract.ai_analysis = analysis
            contract.ai_analyzed_at = datetime.utcnow()
            db.commit()

            logger.info(f"AI analysis complete for contract {contract_id}")
            return {"contract_id": contract_id, "status": "analyzed"}
        finally:
            db.close()

    except Exception as exc:
        logger.error(f"Analysis task failed for {contract_id}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task
def check_expiring_contracts():
    """
    Daily task: flag contracts expiring within 30 days.
    """
    try:
        from app.db.base import SessionLocal
        from app.models.contract import Contract, ContractStatus

        db = SessionLocal()
        try:
            threshold = datetime.utcnow() + timedelta(days=30)
            expiring = db.query(Contract).filter(
                Contract.status == ContractStatus.SIGNED,
                Contract.end_date <= threshold,
                Contract.end_date >= datetime.utcnow(),
                Contract.is_expiry_notified == False
            ).all()

            notified = []
            for contract in expiring:
                contract.is_expiry_notified = True
                notified.append(contract.id)
                logger.info(f"Expiry alert: Contract '{contract.title}' expires on {contract.end_date}")

            db.commit()
            return {"notified_count": len(notified), "contract_ids": notified}
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Expiry check failed: {e}")
        return {"error": str(e)}
