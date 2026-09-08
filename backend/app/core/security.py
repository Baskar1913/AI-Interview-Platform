from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from ..core.config import settings
from ..database import get_db
from ..models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def hash_password(p): return pwd.hash(p)
def verify_password(p,h): return pwd.verify(p,h)
def create_token(user):
    exp=datetime.now(timezone.utc)+timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub":user.id,"role":user.role,"exp":exp},""+settings.jwt_secret,algorithm="HS256")

def current_user(token=Depends(oauth2), db:Session=Depends(get_db)):
    try: data=jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError: raise HTTPException(401,"Invalid or expired token")
    user=db.get(User,data.get("sub"))
    if not user: raise HTTPException(401,"User not found")
    return user

def require_role(role):
    def dep(user=Depends(current_user)):
        if user.role != role: raise HTTPException(403,"Insufficient permissions")
        return user
    return dep
