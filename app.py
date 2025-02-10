# app.py
import os
import logging
import threading
import mimetypes

from flask import Flask, request, jsonify, session
from flask_cors import CORS

# 설정 불러오기
app = Flask(__name__)
app.config.from_object("config.Config")

# CORS 설정 (React 개발 서버 허용)
CORS(app, supports_credentials=True, origins=app.config["CORS_ORIGINS"])

# mimetypes 설정
mimetypes.init()
mimetypes.add_type('application/javascript', '.js', strict=True)

# 사용자 폴더 기본 경로 생성
USERS_BASE = os.path.join(os.getcwd(), "users")
os.makedirs(USERS_BASE, exist_ok=True)

# 동시성 처리를 위한 글로벌 락
file_lock = threading.Lock()

# Firebase 및 헬퍼 함수 import (utils/firebase_helpers.py)
from utils.firebase_helpers import db, generate_user_id

# ----------------- 사용자 관련 헬퍼 함수 -----------------
def get_user_id():
    user_id = session.get("user_id")
    if not user_id:
        raise Exception("로그인이 필요합니다.")
    return user_id

def get_user_base_folder():
    user_id = get_user_id()
    base_folder = os.path.join(USERS_BASE, user_id)
    os.makedirs(base_folder, exist_ok=True)
    return base_folder

def get_user_upload_folder():
    base = get_user_base_folder()
    folder = os.path.join(base, "upload")
    os.makedirs(folder, exist_ok=True)
    return folder

def get_user_model_folder():
    base = get_user_base_folder()
    folder = os.path.join(base, "model")
    os.makedirs(folder, exist_ok=True)
    return folder

def get_user_output_folder():
    base = get_user_base_folder()
    folder = os.path.join(base, "output")
    os.makedirs(folder, exist_ok=True)
    return folder

def get_user_metadata_folder():
    base = get_user_base_folder()
    folder = os.path.join(base, "metadata")
    os.makedirs(folder, exist_ok=True)
    return folder

# 로그인 필요 데코레이터 (일반 사용자용)
from functools import wraps
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({'status': 'error', 'message': '로그인이 필요합니다.'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ----------------- 사용자 관련 API -----------------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    required_fields = ["ID", "PW", "department", "email", "phone", "user_name"]
    for field in required_fields:
        if field not in data:
            return jsonify({"status": "error", "message": f"{field} 필드는 필수입니다."}), 400
    try:
        account_id = data["ID"]
        user_ref = db.collection("User").document(account_id)
        if user_ref.get().exists:
            return jsonify({"status": "error", "message": "이미 사용 중인 ID입니다."}), 400

        numeric_id = generate_user_id()

        base_path = f"./users/{account_id}"
        metadata_path_str = f"{base_path}/metadata"
        model_path_str    = f"{base_path}/model"
        output_path_str   = f"{base_path}/output"
        upload_path_str   = f"{base_path}/upload"

        user_doc = {
            "ID": account_id,
            "PW": data["PW"],
            "department": data["department"],
            "email": data["email"],
            "phone": data["phone"],
            "user_id": numeric_id,
            "user_name": data["user_name"],
            "User_Profile": {
                "RANK": 0,
                "metadata": metadata_path_str,
                "model": model_path_str,
                "output": output_path_str,
                "upload": upload_path_str
            }
        }
        user_ref.set(user_doc)

        os.makedirs(base_path, exist_ok=True)
        os.makedirs(f"{base_path}/metadata", exist_ok=True)
        os.makedirs(f"{base_path}/model", exist_ok=True)
        os.makedirs(f"{base_path}/output", exist_ok=True)
        os.makedirs(f"{base_path}/upload", exist_ok=True)

        return jsonify({"status": "success", "message": "회원가입 성공", "user": user_doc}), 200
    except Exception as e:
        logging.error(str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/get_user', methods=['GET'])
@login_required
def get_user():
    try:
        user_id = session["user_id"]
        user_doc = db.collection("User").document(user_id).get().to_dict()
        if not user_doc:
            return jsonify({"status": "error", "message": "사용자를 찾을 수 없습니다."}), 404
        user_doc.pop("PW", None)
        profile_data = user_doc.get("User_Profile", {})
        return jsonify({"status": "success", "user": user_doc, "profile": profile_data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ----------------- 관리자 API 블루프린트 등록 -----------------
from admin.routes import admin_bp
app.register_blueprint(admin_bp)

if __name__ == "__main__":
    # 필요에 따라 다른 포트로 실행할 수 있습니다.
    app.run(host="0.0.0.0", port=5001, debug=True)
