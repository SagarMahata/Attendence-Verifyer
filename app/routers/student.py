import json
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import models
from ..config import FACE_MATCH_THRESHOLD
from ..database import get_db
from ..schemas import MarkAttendanceRequest
from ..security import require_role
from ..utils.geo import euclidean_distance, haversine_distance_m

router = APIRouter(prefix="/student")
templates = Jinja2Templates(directory="app/templates")


def _expire_stale_polls(db: Session):
    now = datetime.utcnow()
    stale = (
        db.query(models.Poll)
        .filter(models.Poll.is_active.is_(True), models.Poll.expires_at < now)
        .all()
    )
    for p in stale:
        p.is_active = False
        p.ended_at = now
    if stale:
        db.commit()


@router.get("", response_class=HTMLResponse)
def dashboard(
    request: Request,
    user: models.User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    if not user.has_face_enrolled:
        return RedirectResponse("/enroll-face", status_code=302)

    _expire_stale_polls(db)

    active_polls = (
        db.query(models.Poll)
        .filter(models.Poll.is_active.is_(True))
        .order_by(models.Poll.created_at.desc())
        .all()
    )
    my_attendance_poll_ids = {
        a.poll_id
        for a in db.query(models.Attendance).filter(
            models.Attendance.student_id == user.id
        )
    }
    history = (
        db.query(models.Attendance)
        .filter(models.Attendance.student_id == user.id)
        .order_by(models.Attendance.timestamp.desc())
        .limit(20)
        .all()
    )

    return templates.TemplateResponse(
        "student_dashboard.html",
        {
            "request": request,
            "user": user,
            "polls": active_polls,
            "marked_poll_ids": my_attendance_poll_ids,
            "history": history,
        },
    )


@router.get("/polls/{poll_id}", response_class=HTMLResponse)
def mark_attendance_page(
    poll_id: int,
    request: Request,
    user: models.User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    poll = db.query(models.Poll).filter(models.Poll.id == poll_id).first()
    if not poll:
        return RedirectResponse("/student", status_code=302)
    already = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.poll_id == poll.id,
            models.Attendance.student_id == user.id,
        )
        .first()
    )
    return templates.TemplateResponse(
        "mark_attendance.html",
        {"request": request, "user": user, "poll": poll, "already": already},
    )


@router.post("/api/attendance")
def mark_attendance(
    payload: MarkAttendanceRequest,
    user: models.User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    poll = db.query(models.Poll).filter(models.Poll.id == payload.poll_id).first()
    if not poll:
        return {"ok": False, "error": "Poll not found."}
    if not poll.is_active or (poll.expires_at and poll.expires_at < datetime.utcnow()):
        return {"ok": False, "error": "This attendance poll has closed."}

    existing = (
        db.query(models.Attendance)
        .filter(
            models.Attendance.poll_id == poll.id,
            models.Attendance.student_id == user.id,
        )
        .first()
    )
    if existing:
        return {"ok": False, "error": "You've already been marked present for this poll."}

    if not user.has_face_enrolled:
        return {"ok": False, "error": "Enroll your face before marking attendance."}

    # 1. Face verification (always required).
    enrolled = json.loads(user.face_descriptor)
    face_distance = euclidean_distance(enrolled, payload.descriptor)
    if face_distance > FACE_MATCH_THRESHOLD:
        return {
            "ok": False,
            "error": "Face did not match your enrolled identity. Try again in good lighting.",
        }

    # 2. Geofence check, unless the teacher opened anywhere mode.
    distance_m = None
    mode = "geo"
    if poll.anywhere_mode:
        mode = "anywhere"
    else:
        if payload.latitude is None or payload.longitude is None:
            return {"ok": False, "error": "Location access is required for this poll."}
        if poll.latitude is None or poll.longitude is None:
            return {"ok": False, "error": "This poll has no reference location set."}
        distance_m = haversine_distance_m(
            poll.latitude, poll.longitude, payload.latitude, payload.longitude
        )
        if distance_m > poll.radius_m:
            return {
                "ok": False,
                "error": (
                    f"You're {distance_m:.0f} m from class, outside the "
                    f"{poll.radius_m:.0f} m attendance zone."
                ),
            }

    attendance = models.Attendance(
        poll_id=poll.id,
        student_id=user.id,
        distance_m=distance_m,
        face_match_distance=face_distance,
        mode=mode,
    )
    db.add(attendance)
    db.commit()
    return {"ok": True}
