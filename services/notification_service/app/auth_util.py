from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jose.jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user_email(token: str = Depends(oauth2_scheme)):
    try:
       
        payload = jose.jwt.get_unverified_claims(token)
        email: str = payload.get("email") or payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid Token")
        return email
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate credentials")