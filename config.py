import os
from datetime import timedelta


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "postgresql://localhost:5432/journal")
    # Railway livrează scheme "postgres://", pe care SQLAlchemy 2.x nu o mai acceptă.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def _r2_endpoint() -> str:
    endpoint = os.environ.get("R2_ENDPOINT", "").rstrip("/")
    if endpoint:
        return endpoint
    account_id = os.environ.get("R2_ACCOUNT_ID", "")
    return f"https://{account_id}.r2.cloudflarestorage.com" if account_id else ""


_secure_cookies = os.environ.get("COOKIE_SECURE", "1") == "1"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-nu-folosi-in-productie")

    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    JOURNAL_USER = os.environ.get("JOURNAL_USER", "")
    JOURNAL_PASSWORD_HASH = os.environ.get("JOURNAL_PASSWORD_HASH", "")

    # Sesiune persistentă: fără relogare frecventă de pe telefon.
    REMEMBER_COOKIE_DURATION = timedelta(days=90)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = _secure_cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = _secure_cookies

    # Formularele pot sta deschise mult timp (jurnal); tokenul CSRF nu expiră.
    WTF_CSRF_TIME_LIMIT = None

    # Pozele NU trec prin server (presigned PUT direct în R2), deci corpul
    # cererilor către Flask rămâne mic.
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

    R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET = os.environ.get("R2_BUCKET", "")
    R2_ENDPOINT = _r2_endpoint()

    MAX_PHOTOS_PER_ENTRY = 20
    MAX_PHOTO_SIZE = 25 * 1024 * 1024
    PRESIGN_EXPIRES = 3600  # secunde, atât pentru PUT cât și pentru GET
