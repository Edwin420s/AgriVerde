from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import BlockchainRecord, Device, Field
from app.schemas.schemas import DatasetCommit, BlockchainRecordResponse
from app.blockchain.hashing import generate_hash
from app.blockchain.soroban_client import submit_commitment, verify_commitment
from app.core.logging import logger
from app.core.config import settings

router = APIRouter()

@router.post("/blockchain/commit", response_model=BlockchainRecordResponse)
def commit_dataset(commit: DatasetCommit, db: Session = Depends(get_db)):
    # Verify device and field exist
    device = db.query(Device).filter(Device.device_id == commit.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    field = db.query(Field).filter(Field.id == commit.field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    
    # Generate hash (should match incoming)
    computed_hash = generate_hash(commit.dataset_id, commit.device_id, commit.field_id)
    if computed_hash != commit.data_hash:
        raise HTTPException(status_code=400, detail="Hash mismatch")
    
    # Submit to Stellar/Soroban
    tx_hash = submit_commitment(commit.dataset_id, commit.data_hash)
    
    # Save record
    record = BlockchainRecord(
        dataset_id=commit.dataset_id,
        device_id=commit.device_id,
        field_id=commit.field_id,
        data_hash=commit.data_hash,
        stellar_transaction=tx_hash,
        soroban_contract=settings.SOROBAN_CONTRACT_ID
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@router.get("/blockchain/verify/{dataset_id}")
def verify_dataset(dataset_id: str, db: Session = Depends(get_db)):
    record = db.query(BlockchainRecord).filter(BlockchainRecord.dataset_id == dataset_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
        
    # Call Stellar to verify the hash
    is_verified = verify_commitment(dataset_id)
    
    if is_verified and not record.verified:
        record.verified = True
        db.commit()
        
    return {"verified": record.verified, "record": record}