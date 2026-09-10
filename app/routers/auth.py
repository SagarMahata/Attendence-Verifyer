import json

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import models
from ..config import COOKIE_NAME, ACCESS_TOKEN_EXPIRE_MINUTES
from ..database import get_db
from ..schemas import FaceEnrollRequest
from ..security import (
    create_access_token,
    get_current_user,
    hash_password,
    require_user,
    verify_password,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        target = "/teacher" if user.role == "teacher" else "/student"
        return RedirectResponse(target, status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, error: str | None = None):
    return templates.TemplateResponse(
        "register.html", {"request": request, "error": error}
    )


@router.post("/register")
def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db),
):
    if role not in ("teacher", "student"):
        return RedirectResponse("/register?error=Invalid+role", status_code=302)

    existing = db.query(models.User).filter(models.User.email == email.lower()).first()
    if existing:
        return RedirectResponse(
            "/register?error=An+account+with+that+email+already+exists",
            status_code=302,
        )

    user = models.User(
        name=name.strip(),
        email=email.lower().strip(),
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    redirect_to = "/enroll-face" if role == "student" else "/teacher"
    response = RedirectResponse(redirect_to, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return response


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str | None = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == email.lower()).first()
    if not user or not verify_password(password, user.hashed_password):
        return RedirectResponse("/login?error=Invalid+email+or+password", status_code=302)

    token = create_access_token(user.id)
    target = "/teacher" if user.role == "teacher" else "/student"
    response = RedirectResponse(target, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/enroll-face", response_class=HTMLResponse)
def enroll_face_page(request: Request, user: models.User = Depends(require_user)):
    if user.role != "student":
        return RedirectResponse("/teacher", status_code=302)
    return templates.TemplateResponse(
        "face_enroll.html", {"request": request, "user": user}
    )


@router.post("/api/face/enroll")
def enroll_face(
    payload: FaceEnrollRequest,
    user: models.User = Depends(require_user),
    db: Session = Depends(get_db),
):
    user.face_descriptor = json.dumps(payload.descriptor)
    db.commit()
    return {"ok": True}
