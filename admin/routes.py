# admin/routes.py
from flask import Blueprint, request, jsonify, session
from functools import wraps

from utils.firebase_helpers import db, generate_user_id

admin_bp = Blueprint("admin_bp", __name__)

# 관리자 권한 확인 데코레이터 (세션에 "admin_logged_in"이 있어야 함)
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return jsonify({'status': 'error', 'message': '관리자 권한이 필요합니다.'}), 403
        return f(*args, **kwargs)
    return decorated_function

# [관리자] 로그인: 요청으로 전달된 키가 DB에 저장된 관리자 키와 일치하면 세션에 저장
@admin_bp.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    if not data or "value" not in data:
        return jsonify({"status": "error", "message": "관리자 키가 필요합니다."}), 400
    try:
        admin_doc = db.collection("Key").document("secret").get()
        if not admin_doc.exists:
            return jsonify({"status": "error", "message": "관리자 키가 설정되지 않았습니다."}), 500
        stored_key = admin_doc.to_dict().get("value")
        provided_key = data["value"]
        if provided_key != stored_key:
            return jsonify({"status": "error", "message": "잘못된 관리자 키입니다."}), 401
        session["admin_logged_in"] = True
        return jsonify({"status": "success", "message": "관리자 로그인 성공"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# [관리자] 로그아웃: 관리자 세션을 만료합니다.
@admin_bp.route('/api/admin/logout', methods=['POST'])
@admin_required
def admin_logout():
    session.pop("admin_logged_in", None)
    return jsonify({"status": "success", "message": "관리자 로그아웃 되었습니다."}), 200

# [관리자] 전체 사용자 정보 조회 (쿼리 파라미터 user_name으로 검색 가능)
@admin_bp.route('/api/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    try:
        search_query = request.args.get("user_name")
        users = []
        if search_query:
            docs = db.collection("User").where("user_name", "==", search_query).stream()
        else:
            docs = db.collection("User").stream()
        for doc in docs:
            user = doc.to_dict()
            user.pop("PW", None)
            users.append(user)
        return jsonify({"status": "success", "users": users}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# [관리자] 사용자 정보 수정
@admin_bp.route('/api/admin/users/<string:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "업데이트할 데이터가 필요합니다."}), 400
    try:
        doc_ref = db.collection("User").document(user_id)
        if not doc_ref.get().exists:
            return jsonify({"status": "error", "message": "사용자를 찾을 수 없습니다."}), 404
        doc_ref.update(data)
        updated_doc = doc_ref.get().to_dict()
        updated_doc.pop("PW", None)
        return jsonify({"status": "success", "user": updated_doc}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# [관리자] 사용자 정보 삭제 (해당 사용자의 전체 정보를 삭제)
@admin_bp.route('/api/admin/users/<string:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    try:
        doc_ref = db.collection("User").document(user_id)
        if not doc_ref.get().exists:
            return jsonify({"status": "error", "message": "사용자를 찾을 수 없습니다."}), 404
        doc_ref.delete()
        return jsonify({"status": "success", "message": "사용자 정보가 삭제되었습니다."}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@admin_bp.route('/api/admin/users', methods=['POST'])
@admin_required
def register():
    data = request.get_json()
    required_fields = ["ID", "PW", "department", "email", "phone", "user_name"]
    for field in required_fields:
        if field not in data:
            return jsonify({"status": "error", "message": f"{field} 필드는 필수입니다."}), 400

    try:
        account_id = data["ID"]

        # 중복 ID 확인
        user_ref = db.collection("User").document(account_id)
        if user_ref.get().exists:
            return jsonify({"status": "error", "message": "이미 사용 중인 ID입니다."}), 400

        # 고유한 user_id 생성
        numeric_id = generate_user_id()

        # 사용자 폴더 경로 설정
        base_path = f"./users/{account_id}"
        metadata_path_str = f"{base_path}/metadata"
        model_path_str    = f"{base_path}/model"
        output_path_str   = f"{base_path}/output"
        upload_path_str   = f"{base_path}/upload"

        # User 문서에 저장할 데이터
        user_doc = {
            "ID": account_id,
            "PW": data["PW"],
            "department": data["department"],
            "email": data["email"],
            "phone": data["phone"],
            "user_id": numeric_id,
            "user_name": data["user_name"],
            "User_Profile": {               # ⭐ 하위 컬렉션이 아닌 필드로 저장
                "RANK": 0,
                "metadata": metadata_path_str,
                "model": model_path_str,
                "output": output_path_str,
                "upload": upload_path_str
            }
        }

        # Firestore에 저장
        user_ref.set(user_doc)
        return jsonify({
            "status": "success",
            "message": "회원가입 성공",
            "user": user_doc
        }), 200

    except Exception as e:
        logging.error(str(e))
        return jsonify({"status": "error", "message": str(e)}), 500