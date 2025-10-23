"""Main FastAPI application."""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

from app.config import settings
from app import __version__
from app.auth import create_access_token, verify_password, get_password_hash
from app.schemas.auth import Token, TokenData, User, UserInDB

app = FastAPI(
    title="Zammad-Kimai Time Tracking Sync",
    description="Synchronization service for time tracking between Zammad and Kimai",
    version=__version__
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# For demo purposes, we will store a single user in memory (or a mock database)
# In a real application, you would fetch this from your database
DEMO_USER = UserInDB(
    username=settings.ADMIN_USERNAME,
    email="admin@example.com",
    full_name="Admin User",
    disabled=False,
    hashed_password=get_password_hash(settings.ADMIN_PASSWORD)
)

def get_user(username: str):
    if username == DEMO_USER.username:
        return DEMO_USER
    return None

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]):
    if current_user.disabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": __version__
    }


@app.get("/")
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "message": "Zammad-Kimai Time Tracking Sync API",
        "version": __version__,
        "docs": "/api/docs"
    }


# API routers will be added here as we build them
# from app.api import auth, connectors, mappings, sync, conflicts, audit, webhook
# app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
# app.include_router(connectors.router, prefix="/api/connectors", tags=["connectors"])
# app.include_router(mappings.router, prefix="/api/mappings", tags=["mappings"])
# app.include_router(sync.router, prefix="/api/sync", tags=["sync"])
# app.include_router(conflicts.router, prefix="/api/conflicts", tags=["conflicts"])
# app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
# app.include_router(webhook.router, prefix="/api/webhook", tags=["webhook"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
