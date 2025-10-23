from typing import List, Dict, Any, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl

from app.connectors.base import BaseConnector # We will dynamically load connectors
from app.connectors.zammad_connector import ZammadConnector
from app.connectors.kimai_connector import KimaiConnector
from app.schemas.auth import User # Assuming User schema is defined in schemas/auth or similar
from app.main import get_current_active_user # Assuming get_current_active_user is in main.py

router = APIRouter()

# Placeholder for a dynamic connector registry
# In a real app, this would likely involve a database lookup for connector configurations
# and instantiating the correct connector dynamically.
CONNECTOR_TYPES = {
    "zammad": ZammadConnector,
    "kimai": KimaiConnector,
}

class ConnectorConfig(BaseModel):
    """Base Pydantic model for connector configuration."""
    type: str # e.g., "zammad", "kimai"
    base_url: HttpUrl
    api_token: str
    # Add any other common configuration fields here

class ConnectorValidationResult(BaseModel):
    """Result of a connector validation."""
    success: bool
    message: str

class Activity(BaseModel):
    id: Any
    name: str
    project_id: Optional[Any] = None # For Kimai activities linked to projects

@router.post("/validate", response_model=ConnectorValidationResult)
async def validate_connector_config(
    config: ConnectorConfig,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Validates a given connector configuration.
    """
    connector_class = CONNECTOR_TYPES.get(config.type)
    if not connector_class:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown connector type: {config.type}"
        )
    
    # Instantiate the connector with the provided config
    try:
        connector = connector_class(config.model_dump())
        is_valid = await connector.validate_connection()
        if is_valid:
            return ConnectorValidationResult(success=True, message="Connection successful!")
        else:
            return ConnectorValidationResult(success=False, message="Connection failed. Check credentials or URL.")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during connection validation: {e}"
        )

@router.get("/{connector_type}/activities", response_model=List[Activity])
async def get_connector_activities(
    connector_type: str,
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Fetches activities/work types from a specific connector.
    """
    connector_class = CONNECTOR_TYPES.get(connector_type)
    if not connector_class:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown connector type: {connector_type}"
        )
    
    # This is a simplification. In a real app, the connector configuration
    # would be stored in the database and retrieved here.
    # For now, we'll use a dummy config.
    dummy_config = {
        "base_url": "http://example.com", # Replace with actual config from DB
        "api_token": "dummy_token" # Replace with actual config from DB
    }

    try:
        connector = connector_class(dummy_config)
        activities_data = await connector.fetch_activities()
        return [Activity(**activity) for activity in activities_data]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching activities: {e}"
        )
