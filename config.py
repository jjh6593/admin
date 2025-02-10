# config.py
import os

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "fallback_secret_key")
    SESSION_COOKIE_SAMESITE = "None"       # 필요에 따라 "None" 등으로 변경 가능
    SESSION_COOKIE_SECURE = True         # HTTPS 사용 시 True로 변경하세요.
    SESSION_COOKIE_DOMAIN = None
    SESSION_COOKIE_PATH = '/'
    CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
