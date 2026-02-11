import jwt
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from nova_guard.database import get_db
from nova_guard.models.user import User
from nova_guard.config import settings

# Clerk's JWKS endpoint (Public keys)
# In production, cache this!
CLERK_JWKS_URL = "https://balanced-boa-22.clerk.accounts.dev/.well-known/jwks.json" # Derived from PK

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    
    try:
        # 1. Fetch JWKS (Naive implementation: fetch every time. Production: Cache it)
        # Note: PyJWT's PyJWKClient is better for this
        import jwt
        from jwt import PyJWKClient
        
        jwks_client = PyJWKClient(CLERK_JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=None, # Clerk audience might check needed
            options={"verify_exp": True}
        )
        
        user_id = payload.get("sub")
        if not user_id:
             raise HTTPException(status_code=401, detail="Invalid token: no sub")

        # 2. Sync User to DB
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            # Create user on the fly
            user = User(
                id=user_id,
                email=payload.get("email", "") # Email might not be in standard JWT claims depending on config
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
        return user
        
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
