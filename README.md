# Roll Call — Geofenced, Face-Verified Attendance

A FastAPI web app for classroom attendance:

- **Teachers** open a roll call ("poll") from their current location. It's
  live for a set number of minutes, and only students within a configurable
  radius (default **100 m**) can check in.
- **Students** verify their identity by **face recognition** (done in the
  browser, on-device) before they're marked present. Faking someone else's
  attendance requires faking their face on camera.
- **Anywhere mode** — optional, teacher-only toggle per poll — turns off the
  location check entirely, so students can check in from wherever they are.
  Face verification is still required in this mode.

## How it works

- Face matching runs **in the browser** using [face-api.js](https://github.com/vladmandic/face-api)
  (loaded from a CDN, no install needed). A student's face is reduced to a
  128-number "descriptor" on enrollment. On every check-in, a fresh
  descriptor is captured and sent to the server, which compares it
  (Euclidean distance) against the enrolled one — raw video never leaves
  the device.
- Location matching uses the browser's Geolocation API. The teacher's
  location is captured when the poll opens; each student's location is
  compared against it with the Haversine formula, server-side.
- Data lives in a local SQLite file (`attendance.db`), created automatically
  on first run.

## Setup (Windows)

1. Install **Python 3.10+** from [python.org](https://www.python.org/downloads/)
   if you don't have it (check "Add Python to PATH" during install).
2. Open **PowerShell** or **Command Prompt** in this folder
   (`C:\Attendence2`).
3. Create and activate a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
5. Run the server:
   ```
   uvicorn app.main:app --reload
   ```
6. Open **http://127.0.0.1:8000** in your browser.

Camera and geolocation permissions only work over `https://` or on
`localhost` / `127.0.0.1` — running it as above satisfies that, no extra
setup needed. To let other devices on the same Wi-Fi reach it too (e.g.
students' phones), you'd need to serve it over HTTPS (a reverse proxy with
a certificate, or a tool like `ngrok`) — plain `http://<your-ip>:8000` will
have its camera/location access blocked by the browser on any device other
than the host machine.

## Using it

1. **Register** as a teacher, and separately as a student (use a different
   browser/incognito window, or your phone, to test both roles at once).
2. As a **student**, you'll be sent to **Enroll your face** first — look at
   the camera and click "Capture & save." Do this once, somewhere well lit.
3. As a **teacher**, go to your dashboard, fill in a subject, radius, and
   duration, then click **Start poll**. Allow location access when asked
   (skip this by turning on **Anywhere mode** instead).
4. As the **student**, refresh the dashboard — the open poll appears. Click
   **Check in**, allow camera (and location, unless anywhere mode is on),
   and hold still — it verifies automatically once your face is detected.
5. Back on the **teacher's** poll page, the student appears in the present
   list in real time (refresh to see updates), along with their distance
   from class or an "anywhere" tag.

## Project layout

```
app/
  main.py            FastAPI app, routing, startup
  config.py           Settings: secret key, radius default, face threshold
  database.py          SQLAlchemy engine/session
  models.py            User, Poll, Attendance tables
  schemas.py            Pydantic request bodies
  security.py           Password hashing + cookie-based JWT auth
  utils/geo.py            Haversine distance + descriptor distance
  routers/
    auth.py                Register, login, logout, face enrollment
    teacher.py               Dashboard, create/end poll, poll detail
    student.py                 Dashboard, check-in page, attendance API
  templates/                  Jinja2 HTML pages
  static/css/style.css          Styling
  static/js/face.js               face-api.js capture + matching UI
  static/js/geolocation.js          Geolocation helper
requirements.txt
```

## Notes & things to harden before real deployment

- The face-match threshold (`FACE_MATCH_THRESHOLD` in `config.py`, default
  `0.5`) trades off false accepts vs. false rejects — tune it if it's too
  strict or too lenient for your camera conditions.
- `SECRET_KEY` is auto-generated per run unless you set the
  `ATTENDANCE_SECRET_KEY` environment variable — set one for a real
  deployment so login sessions survive a server restart.
- There's no server-side liveness check (e.g. blink detection) against a
  printed photo or a video replay — add one (face-api.js exposes landmark
  data you could use for a basic liveness heuristic) if that's a real
  threat in your setting.
- Each student can check into a given poll only once (`UniqueConstraint` on
  poll + student).
