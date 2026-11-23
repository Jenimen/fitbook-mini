"""FitBook mini – edzőterem-órafoglaló REST API.

Üzleti szabályok:
- Az admin órát hozhat létre (név, edző, időpont, kapacitás).
- A tag helyet foglalhat; ha az óra tele van, várólistára kerül.
- Lemondáskor az első várólistás automatikusan bekerül (előléptetés).
- Egy tag egy órára csak egyszer foglalhat.
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from app import db

APP_VERSION = os.getenv("APP_VERSION", "dev")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    yield


app = FastAPI(title="FitBook mini", version=APP_VERSION, lifespan=lifespan)


class SessionIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    trainer: str = Field(min_length=2, max_length=60)
    starts_at: datetime
    capacity: int = Field(ge=1, le=50)


class BookingIn(BaseModel):
    member: str = Field(min_length=2, max_length=60)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": APP_VERSION}


@app.get("/sessions")
def list_sessions() -> list[dict]:
    return db.list_sessions()


@app.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(body: SessionIn, x_role: str = Header(default="member")) -> dict:
    if x_role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Csak admin hozhat létre órát.")
    return db.create_session(body.name, body.trainer, body.starts_at.isoformat(), body.capacity)


@app.get("/sessions/{session_id}")
def get_session(session_id: int) -> dict:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nincs ilyen óra.")
    return session


@app.post("/sessions/{session_id}/bookings", status_code=status.HTTP_201_CREATED)
def book(session_id: int, body: BookingIn) -> dict:
    session = db.get_session(session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nincs ilyen óra.")
    if db.has_open_booking(session_id, body.member):
        raise HTTPException(status.HTTP_409_CONFLICT, "Erre az órára már van foglalásod.")
    booking_status = "ACTIVE" if session["free_places"] > 0 else "WAITLISTED"
    return db.create_booking(session_id, body.member, booking_status)


@app.delete("/bookings/{booking_id}")
def cancel(booking_id: int) -> dict:
    booking = db.get_booking(booking_id)
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nincs ilyen foglalás.")
    if booking["status"] == "CANCELLED":
        raise HTTPException(status.HTTP_409_CONFLICT, "A foglalás már le van mondva.")
    promoted = db.cancel_booking(booking_id)
    return {"cancelled": booking_id, "promoted": promoted}
