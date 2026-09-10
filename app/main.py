from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import models
from .database import Base, engine
from .routers import auth, student, teacher

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Attendance — Roll Call")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(HTTPException)
async def redirect_unauthenticated(request, exc: HTTPException):
    # require_user() raises a 303 HTTPException with a Location header when
    # nobody is logged in; turn that into a real redirect for the browser.
    if exc.status_code == 303 and "Location" in (exc.headers or {}):
        return RedirectResponse(exc.headers["Location"], status_code=303)
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(auth.router)
app.include_router(teacher.router)
app.include_router(student.router)
