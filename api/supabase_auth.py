from supabase import create_client, Client
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from config import settings
import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_supabase_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_anon_secret)

def verify_token(token: str = Depends(oauth2_scheme), supabase: Client = Depends(get_supabase_client)):
    try:
        # Decode the token to check for expiration without verifying the signature
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        
        # This will verify the token and return the user
        user_response = supabase.auth.get_user(token)
        
        if user_response.user:
            return user_response.user
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )