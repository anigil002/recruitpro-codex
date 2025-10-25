"""FastAPI dependency helpers."""

from typing import Optional

from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from functools import lru_cache

from sqlalchemy.exc import OperationalError

from .database import get_session, init_db
from .models import User
from .utils.security import decode_token
from .services.bootstrap import ensure_super_admin

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@lru_cache(maxsize=1)
def _ensure_database_initialized() -> None:
    """Initialise the database schema once per process.

    When the application starts for the first time the SQLite file may not yet
    exist.  The FastAPI lifespan hook is responsible for calling
    :func:`init_db`, however certain execution paths – for example when running
    via the Electron renderer or unit tests that import dependencies directly –
    can hit the dependency chain before the lifespan hook has a chance to run.
    In that scenario ``ensure_super_admin`` would try to query the ``users``
    table and trigger an ``OperationalError`` because the schema has not been
    created yet.  By guarding initialisation here we make the dependency more
    robust regardless of how the app is invoked.
    """

    init_db()


def get_db() -> Session:
    _ensure_database_initialized()
    with get_session() as session:
        try:
            ensure_super_admin(session)
        except OperationalError:
            # If the bootstrap query fails because the tables are still
            # missing, initialise the schema and try again.  This is mostly
            # defensive – ``_ensure_database_initialized`` should have created
            # the tables – but keeps the dependency resilient during cold
            # starts and test runs.
            init_db()
            ensure_super_admin(session)
        yield session


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_optional_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None

    user_id = decode_token(token)
    if not user_id:
        return None

    return db.get(User, user_id)


def get_stream_user(
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> User:
    credential: Optional[str] = None

    if authorization:
        scheme, _, header_token = authorization.partition(" ")
        if scheme.lower() == "bearer" and header_token:
            credential = header_token

    if not credential and token:
        credential = token

    if not credential:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token")

    user_id = decode_token(credential)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user
