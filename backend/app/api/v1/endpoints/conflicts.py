from typing import List, Annotated, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.conflict import Conflict as DBConflict
from app.schemas.conflict import ConflictInDB, ConflictCreate, ConflictUpdate, BasicConflictInDB
from app.schemas.auth import User
from app.auth import get_current_active_user
from app.constants.conflict_reasons import ReasonCode

router = APIRouter()

@router.post("/", response_model=ConflictInDB, status_code=status.HTTP_201_CREATED)
async def create_conflict(
    conflict: ConflictCreate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Create a new conflict record."""
    db_conflict = DBConflict(**conflict.model_dump())
    db.add(db_conflict)
    db.commit()
    db.refresh(db_conflict)
    return db_conflict

@router.get("/", response_model=List[ConflictInDB])
async def read_conflicts(
    include_rich: bool = Query(True),
    skip: int = 0,
    limit: int = 100,
    resolution_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Retrieve multiple conflict records, with optional rich metadata."""
    query = db.query(DBConflict)
    if resolution_status:
        query = query.filter(DBConflict.resolution_status == resolution_status)
    conflicts = query.offset(skip).limit(limit).all()
    if not include_rich:
        # Return basic without rich fields if needed, but for now use ConflictInDB as it's extended
        return [BasicConflictInDB.model_validate(c) for c in conflicts]
    return conflicts

@router.get("/{conflict_id}", response_model=ConflictInDB)
async def read_conflict(
    conflict_id: int,
    include_rich: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Retrieve a single conflict record by ID, with optional rich metadata."""
    db_conflict = db.query(DBConflict).filter(DBConflict.id == conflict_id).first()
    if db_conflict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")
    if not include_rich:
        return BasicConflictInDB.model_validate(db_conflict)
    return db_conflict

@router.patch("/{conflict_id}", response_model=ConflictInDB)
async def update_conflict(
    conflict_id: int,
    conflict: ConflictUpdate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Update an existing conflict record."""
    db_conflict = db.query(DBConflict).filter(DBConflict.id == conflict_id).first()
    if db_conflict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")
    
    for key, value in conflict.model_dump(exclude_unset=True).items():
        setattr(db_conflict, key, value)
    
    if conflict.resolution_status == "resolved" and not db_conflict.resolved_at:
        db_conflict.resolved_at = datetime.now()
        db_conflict.resolved_by = current_user.username if current_user else None

    db.commit()
    db.refresh(db_conflict)
    return db_conflict

@router.delete("/{conflict_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conflict(
    conflict_id: int,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Delete a conflict record."""
    db_conflict = db.query(DBConflict).filter(DBConflict.id == conflict_id).first()
    if db_conflict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")
    
    db.delete(db_conflict)
    db.commit()
