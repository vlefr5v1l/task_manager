from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, verify_password
from src.core.config import settings
from src.db.session import get_db
from src.schemas.token import Token, TokenPayload
from src.schemas.user import User, UserCreate
from src.services import user as user_service

router = APIRouter()