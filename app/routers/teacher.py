from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import models
from ..config import DEFAULT_POLL_DURATION_MINUTES, DEFAULT_POLL_RADIUS_M
from ..database import get_db
from ..schemas import PollCreateRequest
from ..security import require_role

router = APIRouter(prefix="/teacher")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request,
    user: models.User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    polls = (
        db.query(models.Poll)
        .filter(models.Poll.teacher_id == user.id)
        .order_by(models.Poll.created_at.desc())
        .all()
    )
    # Auto-expire polls whose timer has run out.
    now = datetime.utcnow()
    changed = False
    for p in polls:
        if p.is_active and p.expires_at and p.expires_at < now:
            p.is_active = False
            p.ended_at = now
            changed = True
    if changed:
        db.commit()

    return templates.TemplateResponse(
        "teacher_dashboard.html",
        {
            "request": request,
            "user": user,
            "polls": polls,
            "default_radius": DEFAULT_POLL_RADIUS_M,
            "default_duration": DEFAULT_POLL_DURATION_MINUTES,
        },
    )


@router.post("/polls")
def create_poll(
    payload: PollCreateRequest,
    user: models.User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    if not payload.anywhere_mode and (
        payload.latitude is None or payload.longitude is None
    ):
        return {"ok": False, "error": "Location is required unless anywhere mode is on."}

    poll = models.Poll(
        teacher_id=user.id,
        subject=payload.subject.strip() or "Class",
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_m=payload.radius_m or DEFAULT_POLL_RADIUS_M,
        anywhere_mode=payload.anywhere_mode,
        is_active=True,
        expires_at=datetime.utcnow()
        + timedelta(minutes=payload.duration_minutes or DEFAULT_POLL_DURATION_MINUTES),
    )
    db.add(poll)
    db.commit()
    db.refresh(poll)
    return {"ok": True, "poll_id": poll.id}


@router.post("/polls/{poll_id}/end")
def end_poll(
    poll_id: int,
    user: models.User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    poll = (
        db.query(models.Poll)
        .filter(models.Poll.id == poll_id, models.Poll.teacher_id == user.id)
        .first()
    )
    if not poll:
        return {"ok": False, "error": "Poll not found"}
    poll.is_active = False
    poll.ended_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.get("/polls/{poll_id}", response_class=HTMLResponse)
def poll_detail(
    poll_id: int,
    request: Request,
    user: models.User = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    poll = (
        db.query(models.Poll)
        .filter(models.Poll.id == poll_id, models.Poll.teacher_id == user.id)
        .first()
    )
    if not poll:
        return RedirectResponse("/teacher", status_code=302)

    attendances = (
        db.query(models.Attendance)
        .filter(models.Attendance.poll_id == poll.id)
        .order_by(models.Attendance.timestamp.asc())
        .all()
    )
    return templates.TemplateResponse(
        "poll_detail.html",
        {"request": request, "user": user, "poll": poll, "attendances": attendances},
    )
