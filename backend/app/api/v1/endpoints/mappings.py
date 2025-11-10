from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.mapping import ActivityMapping
from app.schemas.mapping import MappingCreate, MappingUpdate, MappingInDB
from app.schemas.auth import User
from app.auth import get_current_active_user
from app.utils.audit_logger import create_audit_log

router = APIRouter()

@router.post("/", response_model=MappingInDB, status_code=status.HTTP_201_CREATED)
async def create_mapping(
    request: Request,
    mapping: MappingCreate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Create a new activity mapping."""
    # Check for existing unique mapping
    if db.query(ActivityMapping).filter(
        ActivityMapping.zammad_type_id == mapping.zammad_type_id,
        ActivityMapping.kimai_activity_id == mapping.kimai_activity_id
    ).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mapping for this Zammad type and Kimai activity already exists"
        )
    
    db_mapping = ActivityMapping(**mapping.model_dump())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    
    # Log mapping creation
    create_audit_log(
        db=db,
        request=request,
        action="mapping_created",
        entity_type="mapping",
        entity_id=db_mapping.id,
        user=current_user.username if current_user else None,
        details={
            "zammad_type": mapping.zammad_type_name,
            "kimai_activity": mapping.kimai_activity_name
        }
    )
    
    return db_mapping

@router.get("/", response_model=List[MappingInDB])
async def read_mappings(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Retrieve multiple activity mappings."""
    mappings = db.query(ActivityMapping).offset(skip).limit(limit).all()
    return mappings

@router.get("/{mapping_id}", response_model=MappingInDB)
async def read_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Retrieve a single activity mapping by ID."""
    db_mapping = db.query(ActivityMapping).filter(ActivityMapping.id == mapping_id).first()
    if db_mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    return db_mapping

@router.patch("/{mapping_id}", response_model=MappingInDB)
async def update_mapping(
    request: Request,
    mapping_id: int,
    mapping: MappingUpdate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Update an existing activity mapping."""
    db_mapping = db.query(ActivityMapping).filter(ActivityMapping.id == mapping_id).first()
    if db_mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    
    update_data = mapping.model_dump(exclude_unset=True)
    # Check uniqueness on update if key fields changed
    if "zammad_type_id" in update_data or "kimai_activity_id" in update_data:
        existing = db.query(ActivityMapping).filter(
            ActivityMapping.zammad_type_id == (update_data.get("zammad_type_id", db_mapping.zammad_type_id)),
            ActivityMapping.kimai_activity_id == (update_data.get("kimai_activity_id", db_mapping.kimai_activity_id)),
            ActivityMapping.id != mapping_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mapping for this Zammad type and Kimai activity already exists"
            )
    
    for key, value in update_data.items():
        setattr(db_mapping, key, value)
    
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    
    # Log mapping update
    create_audit_log(
        db=db,
        request=request,
        action="mapping_updated",
        entity_type="mapping",
        entity_id=db_mapping.id,
        user=current_user.username if current_user else None,
        details={
            "updated_fields": list(update_data.keys()),
            "zammad_type": db_mapping.zammad_type_name,
            "kimai_activity": db_mapping.kimai_activity_name
        }
    )
    
    return db_mapping

@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    request: Request,
    mapping_id: int,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Delete an activity mapping."""
    db_mapping = db.query(ActivityMapping).filter(ActivityMapping.id == mapping_id).first()
    if db_mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    
    # Log mapping deletion before removing
    create_audit_log(
        db=db,
        request=request,
        action="mapping_deleted",
        entity_type="mapping",
        entity_id=db_mapping.id,
        user=current_user.username if current_user else None,
        details={
            "zammad_type": db_mapping.zammad_type_name,
            "kimai_activity": db_mapping.kimai_activity_name
        }
    )
    
    db.delete(db_mapping)
    db.commit()
    return None
