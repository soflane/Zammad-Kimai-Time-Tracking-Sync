from typing import List, Annotated, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.conflict import Conflict as DBConflict
from app.schemas.conflict import ConflictInDB, ConflictCreate, ConflictUpdate
from app.schemas.auth import User # For dependency `get_current_active_user`
from app.auth import get_current_active_user # Assuming get_current_active_user is in main.py

router = APIRouter()

@router.post("/", response_model=ConflictInDB, status_code=status.HTTP_201_CREATED)
async def create_conflict(
    conflict: ConflictCreate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None # Require auth
):
    """Create a new conflict record."""
    db_conflict = DBConflict(**conflict.model_dump())
    db.add(db_conflict)
    db.commit()
    db.refresh(db_conflict)
    return db_conflict

@router.get("/", response_model=List[ConflictInDB])
async def read_conflicts(
    skip: int = 0,
    limit: int = 100,
    resolution_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None # Require auth
):
    """Retrieve multiple conflict records."""
    query = db.query(DBConflict)
    if resolution_status:
        query = query.filter(DBConflict.resolution_status == resolution_status)
    conflicts = query.offset(skip).limit(limit).all()
    return conflicts

@router.get("/{conflict_id}", response_model=ConflictInDB)
async def read_conflict(
    conflict_id: int,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None # Require auth
):
    """Retrieve a single conflict record by ID."""
    db_conflict = db.query(DBConflict).filter(DBConflict.id == conflict_id).first()
    if db_conflict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")
    return db_conflict

@router.patch("/{conflict_id}", response_model=ConflictInDB)
async def update_conflict(
    conflict_id: int,
    conflict: ConflictUpdate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None # Require auth
):
    """Update an existing conflict record."""
    db_conflict = db.query(DBConflict).filter(DBConflict.id == conflict_id).first()
    if db_conflict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")
    
    for key, value in conflict.model_dump(exclude_unset=True).items():
        setattr(db_conflict, key, value)
    
    if conflict.resolution_status == "resolved" and not db_conflict.resolved_at:
        db_conflict.resolved_at = datetime.now()
        db_conflict.resolved_by = current_user.username # Assume current_user is the resolver

    db.add(db_conflict)
    db.commit()
    db.refresh(db_conflict)
    return db_conflict

@router.delete("/{conflict_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conflict(
    conflict_id: int,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None # Require auth
):
    """Delete a conflict record."""
    db_conflict = db.query(DBConflict).filter(DBConflict.id == conflict_id).first()
    if db_conflict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")
    
    db.delete(db_conflict)
    db.commit()
    return
