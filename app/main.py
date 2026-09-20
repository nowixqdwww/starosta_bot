import os
import secrets
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import get_tg_user
from .db import Base, engine, get_db
from .models import Group, User
from .schedule import router as schedule_router

Base.metadata.create_all(engine)
app = FastAPI()

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # без похожих символов


class LeaderIn(BaseModel):
    name: Text
    group_name: Text
    institution: Text


class StudentIn(BaseModel):
    name: Text
    invite_code: Text


def new_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
        if not db.scalar(select(Group).where(Group.invite_code == code)):
            return code


def invite_link(code: str) -> str:
    bot, short = os.getenv("BOT_USERNAME", ""), os.getenv("APP_SHORTNAME", "app")
    return f"https://t.me/{bot}/{short}?startapp={code}"


def user_out(user: User) -> dict:
    out = {
        "registered": True,
        "name": user.name,
        "role": user.role,
        "group": {"name": user.group.name, "institution": user.group.institution},
    }
    if user.role == "leader":
        out["group"]["invite_code"] = user.group.invite_code
        out["group"]["invite_link"] = invite_link(user.group.invite_code)
    return out


@app.get("/api/me")
def me(tg=Depends(get_tg_user), db: Session = Depends(get_db)):
    user = db.get(User, tg["id"])
    if not user:
        return {"registered": False, "tg_name": tg.get("first_name", "")}
    return user_out(user)


@app.get("/api/invite/{code}")
def check_invite(code: str, tg=Depends(get_tg_user), db: Session = Depends(get_db)):
    group = db.scalar(select(Group).where(Group.invite_code == code.strip().upper()))
    if not group:
        raise HTTPException(404, "Код не найден")
    return {"group_name": group.name, "institution": group.institution}


@app.post("/api/register/leader")
def register_leader(data: LeaderIn, tg=Depends(get_tg_user), db: Session = Depends(get_db)):
    if db.get(User, tg["id"]):
        raise HTTPException(409, "Уже зарегистрирован")
    group = Group(name=data.group_name, institution=data.institution, invite_code=new_code(db))
    db.add(group)
    db.flush()
    db.add(User(tg_id=tg["id"], name=data.name, role="leader", group_id=group.id))
    db.commit()
    return user_out(db.get(User, tg["id"]))


@app.post("/api/register/student")
def register_student(data: StudentIn, tg=Depends(get_tg_user), db: Session = Depends(get_db)):
    if db.get(User, tg["id"]):
        raise HTTPException(409, "Уже зарегистрирован")
    group = db.scalar(select(Group).where(Group.invite_code == data.invite_code.strip().upper()))
    if not group:
        raise HTTPException(404, "Код не найден")
    db.add(User(tg_id=tg["id"], name=data.name, role="student", group_id=group.id))
    db.commit()
    return user_out(db.get(User, tg["id"]))


app.include_router(schedule_router)

# Mini App: index.html, style.css, app.js. Должно идти после всех /api маршрутов.
app.mount("/", StaticFiles(directory=Path(__file__).parent.parent / "static", html=True), name="static")
