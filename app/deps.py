from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from .auth import get_tg_user
from .db import get_db
from .models import User


def current_user(tg=Depends(get_tg_user), db: Session = Depends(get_db)) -> User:
    user = db.get(User, tg["id"])
    if not user:
        raise HTTPException(403, "Сначала зарегистрируйся")
    return user


def leader_only(user: User = Depends(current_user)) -> User:
    if user.role != "leader":
        raise HTTPException(403, "Это может делать только староста")
    return user
