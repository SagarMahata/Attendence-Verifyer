import os
import secrets


SECRET_KEY = os.environ.get("ATTENDANCE_SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours

COOKIE_NAME = "attendance_session"

# Default geofence radius (metres) a teacher's poll uses unless changed.
DEFAULT_POLL_RADIUS_M = 100.0

# How long a normal poll stays open if the teacher doesn't close it manually.
DEFAULT_POLL_DURATION_MINUTES = 15

# Face match threshold: face-api.js descriptors are 128-d vectors: a
# Euclidean distance below this value is treated as "the same person".
FACE_MATCH_THRESHOLD = 0.5

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

POSTGRES_USER = os.environ.get("POSTGRES_USER", "attendance_user")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "attendance")

DATABASE_URL = os.environ.get(
    "ATTENDANCE_DATABASE_URL",
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)
