from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    institution: Mapped[str]
    invite_code: Mapped[str] = mapped_column(unique=True, index=True)
    # за сколько минут до пары слать опрос (понадобится на шаге 4)
    remind_before_min: Mapped[int] = mapped_column(default=30)


class User(Base):
    __tablename__ = "users"

    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    name: Mapped[str]
    role: Mapped[str]  # "leader" | "student"
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))

    group: Mapped[Group] = relationship()


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    weekday: Mapped[int]  # 0 = понедельник ... 6 = воскресенье
    start_time: Mapped[str]  # "HH:MM"
    title: Mapped[str]
