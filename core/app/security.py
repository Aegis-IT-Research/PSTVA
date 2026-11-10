import hashlib
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

import jwt
from fastapi import Header, HTTPException

# Secret key for JWT, set in .env
SECRET_KEY = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token expiration time in minutes

# In-memory storage for users (replace with a database in production)
USERS_DB: Dict[str, str] = {}  # Example: {"default": "hashed_password"}

# Add default user
DEFAULT_USERNAME = os.environ["APP_USER"]
DEFAULT_PASSWORD = os.environ["APP_PASSWORD"]
USERS_DB[DEFAULT_USERNAME] = hashlib.sha256(DEFAULT_PASSWORD.encode()).hexdigest()


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""

    return hashlib.sha256(password.encode()).hexdigest()


def authenticate_user(username: str, password: str) -> bool:
    """Authenticate a user by verifying their username and password."""

    hashed_password = USERS_DB.get(username)
    if not hashed_password or hashed_password != hash_password(password):
        return False
    return True


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def validate_api_key(x_api_key: str = Header(...)):
    """Validate the provided API token."""

    try:
        payload = jwt.decode(x_api_key, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid API Key")


def login_user(username: str, password: str) -> str:
    """Authenticate a user and generate a JWT token."""

    if not authenticate_user(username, password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    return access_token


def logout_user(username: str):
    """Log out a user (JWT tokens are stateless, so this is optional)."""

    _ = username
