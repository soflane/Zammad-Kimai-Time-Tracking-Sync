from typing import List, Dict, Any, Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.database import get_db
from app.connectors.base import BaseConnector
from app.connectors.zammad_connector import ZammadConnector
from app.connectors.kimai_connector import KimaiConnector
from app.models.connector import Connector as DBConnector
from app.schemas.connector import ConnectorCreate, ConnectorUpdate, ConnectorInDB
from app.schemas.auth import User 
from app.auth import get_current_active_user
from app.utils.encrypt import encrypt_data, decrypt_data

class TestConnectorRequest(BaseModel):
    id: Optional[int] = None
    type: Optional[str] = None
    base_url: Optional[HttpUrl] = None
    api_token: Optional[str] = None

import logging
log = logging.getLogger(__name__)

router = APIRouter()

CONNECTOR_TYPES = {
    "zammad": ZammadConnector,
    "kimai": KimaiConnector,
}

class ConnectorValidationResult(BaseModel):
    valid: bool
    message: str

class Activity(BaseModel):
    id: Any
    name: str
    project_id: Optional[Any] = None 


async def get_connector_instance(db_conn: DBConnector) -> BaseConnector:
    connector_class = CONNECTOR_TYPES.get(db_conn.type)
    if not connector_class:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown connector type: {db_conn.type}"
        )
    
    base_url = str(db_conn.base_url)
    if base_url.startswith("http://"):
        base_url = base_url.replace("http://", "https://")
        # For now, just use HTTPS for the instance; update DB on successful validation if needed
    
    decrypted_token = decrypt_data(db_conn.api_token)
    config = {
        "base_url": base_url,
        "api_token": decrypted_token,
        "settings": db_conn.settings or {}
    }
    return connector_class(config)

@router.post("/", response_model=ConnectorInDB, status_code=status.HTTP_201_CREATED)
async def create_connector(
    connector: ConnectorCreate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Create a new connector configuration."""
    if db.query(DBConnector).filter(DBConnector.name == connector.name).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connector with this name already exists")
    
    if connector.type not in CONNECTOR_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported connector type: {connector.type}")

    # Encrypt API token before saving
    encrypted_api_token = encrypt_data(connector.api_token)
    
    db_connector = DBConnector(
        name=connector.name,
        type=connector.type,
        base_url=str(connector.base_url),
        api_token=encrypted_api_token,
        is_active=connector.is_active,
        settings=connector.settings
    )
    db.add(db_connector)
    db.commit()
    db.refresh(db_connector)
    # Mask API token for response
    db_connector.api_token = "********"
    return db_connector

@router.get("/", response_model=List[ConnectorInDB])
async def read_connectors(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Retrieve multiple connector configurations."""
    connectors = db.query(DBConnector).offset(skip).limit(limit).all()
    # Mask API tokens for response
    for conn in connectors:
        conn.api_token = "********"
    return connectors

@router.get("/{connector_id}", response_model=ConnectorInDB)
async def read_connector(
    connector_id: int,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Retrieve a single connector configuration by ID."""
    db_connector = db.query(DBConnector).filter(DBConnector.id == connector_id).first()
    if db_connector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")
    # Mask API token for response
    db_connector.api_token = "********"
    return db_connector

@router.patch("/{connector_id}", response_model=ConnectorInDB)
async def update_connector(
    connector_id: int,
    connector: ConnectorUpdate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Update an existing connector configuration."""
    db_connector = db.query(DBConnector).filter(DBConnector.id == connector_id).first()
    if db_connector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")
    
    update_data = connector.model_dump(exclude_unset=True)
    if "api_token" in update_data and update_data["api_token"]:
        update_data["api_token"] = encrypt_data(update_data["api_token"])
    if "base_url" in update_data and update_data["base_url"]:
        update_data["base_url"] = str(update_data["base_url"])

    for key, value in update_data.items():
        setattr(db_connector, key, value)
    
    db.add(db_connector)
    db.commit()
    db.refresh(db_connector)
    db_connector.api_token = "********" # Mask API token for response
    return db_connector

@router.delete("/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connector(
    connector_id: int,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """Delete a connector configuration."""
    db_connector = db.query(DBConnector).filter(DBConnector.id == connector_id).first()
    if db_connector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")
    
    db.delete(db_connector)
    db.commit()
    return

@router.post("/test", response_model=ConnectorValidationResult)
async def test_connector_connection(
    request: TestConnectorRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """
    Tests a connector connection. For new: provide type, base_url, api_token.
    For existing: provide id, optionally override base_url/api_token.
    """
    if request.id:
        # Existing connector
        db_connector = db.query(DBConnector).filter(DBConnector.id == request.id).first()
        if db_connector is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")
        
        # Override if provided
        if request.base_url:
            db_connector.base_url = str(request.base_url)
        if request.api_token:
            db_connector.api_token = encrypt_data(request.api_token)
        
        try:
            connector_instance = await get_connector_instance(db_connector)
            is_valid = await connector_instance.validate_connection()
            if is_valid:
                return ConnectorValidationResult(valid=True, message="Connection successful!")
            else:
                return ConnectorValidationResult(valid=False, message="Connection failed. Check credentials or URL.")
        except Exception as e:
            return ConnectorValidationResult(valid=False, message=f"Validation error: {str(e)}")
    else:
        # New connector
        if not all([request.type, request.base_url, request.api_token]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="For new connectors, type, base_url, and api_token are required."
            )
        
        if request.type not in CONNECTOR_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported connector type: {request.type}"
            )
        
        # Temp config for test
        temp_connector = DBConnector(
            type=request.type,
            base_url=str(request.base_url),
            api_token=encrypt_data(request.api_token),
            settings={}
        )
        
        try:
            connector_instance = await get_connector_instance(temp_connector)
            is_valid = await connector_instance.validate_connection()
            if is_valid:
                return ConnectorValidationResult(valid=True, message="Connection successful!")
            else:
                return ConnectorValidationResult(valid=False, message="Connection failed. Check credentials or URL.")
        except Exception as e:
            return ConnectorValidationResult(valid=False, message=f"Validation error: {str(e)}")


@router.post("/validate", response_model=ConnectorValidationResult)
async def validate_connector_config(
    connector_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """
    Validates a given connector configuration stored in the database (legacy).
    """
    db_connector = db.query(DBConnector).filter(DBConnector.id == connector_id).first()
    if db_connector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")
    
    try:
        connector_instance = await get_connector_instance(db_connector)
        is_valid = await connector_instance.validate_connection()
        if is_valid:
            return ConnectorValidationResult(valid=True, message="Connection successful!")
        else:
            return ConnectorValidationResult(valid=False, message="Connection failed. Check credentials or URL.")
    except Exception as e:
        return ConnectorValidationResult(valid=False, message=f"Validation error: {str(e)}")

@router.get("/{connector_id}/activities", response_model=List[Activity])
async def get_connector_activities(
    connector_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """
    Fetches activities/work types from a specific connector stored in the database.
    """
    db_connector = db.query(DBConnector).filter(DBConnector.id == connector_id).first()
    if db_connector is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")
    
    try:
        connector_instance = await get_connector_instance(db_connector)
        activities_data = await connector_instance.fetch_activities()
        return [Activity(**activity) for activity in activities_data]
    except ValueError as e:
        # Specific errors from connector (e.g., invalid token, permissions)
        log.error(f"Error fetching activities for connector {connector_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Unexpected errors
        log.error(f"Unexpected error fetching activities for connector {connector_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch activities: {str(e)}"
        )
