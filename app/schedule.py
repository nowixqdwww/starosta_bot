from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import get_db
from .deps import current_user, leader_only
from .models import Lesson, User

router = APIRouter(prefix="/api/schedule")

MAX_LESSONS = 100  # защита от мусора в одной группе

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Time = Annotated[str, StringConstraints(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]


class LessonIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    title: Title
    start_time: Time


def lesson_out(l: Lesson) -> dict:
    return {"id": l.id, "weekday": l.weekday, "title": l.title, "start_time": l.start_time}


def own_lesson(db: Session, user: User, lesson_id: int) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if not lesson or lesson.group_id != user.group_id:
        raise HTTPException(404, "Пара не найдена")
    return lesson


@router.get("")
def list_lessons(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Lesson)
        .where(Lesson.group_id == user.group_id)
        .order_by(Lesson.weekday, Lesson.start_time)
    ).all()
    return [lesson_out(l) for l in rows]


@router.post("")
def add_lesson(data: LessonIn, user: User = Depends(leader_only), db: Session = Depends(get_db)):
    count = db.scalar(select(func.count()).select_from(Lesson).where(Lesson.group_id == user.group_id))
    if count >= MAX_LESSONS:
        raise HTTPException(400, "Слишком много пар в расписании")
    lesson = Lesson(group_id=user.group_id, **data.model_dump())
    db.add(lesson)
    db.commit()
    return lesson_out(lesson)


@router.put("/{lesson_id}")
def edit_lesson(lesson_id: int, data: LessonIn, user: User = Depends(leader_only), db: Session = Depends(get_db)):
    lesson = own_lesson(db, user, lesson_id)
    for key, value in data.model_dump().items():
        setattr(lesson, key, value)
    db.commit()
    return lesson_out(lesson)


@router.delete("/{lesson_id}")
def delete_lesson(lesson_id: int, user: User = Depends(leader_only), db: Session = Depends(get_db)):
    db.delete(own_lesson(db, user, lesson_id))
    db.commit()
    return {"ok": True}
