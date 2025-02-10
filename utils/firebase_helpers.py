import firebase_admin
from firebase_admin import credentials, firestore
import secrets

# Firebase가 아직 초기화되지 않았다면 초기화합니다.
if not firebase_admin._apps:
    cred = credentials.Certificate("./serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def generate_user_id():
    """
    Firestore의 Counters 컬렉션 내 'user_counter' 문서를 이용하여
    고유한 user_id(숫자)를 생성합니다.
    """
    counter_ref = db.collection("Counters").document("user_counter")
    transaction = db.transaction()

    @firestore.transactional
    def update_counter(transaction, ref):
        snapshot = next(transaction.get(ref), None)
        if snapshot and snapshot.exists:
            data = snapshot.to_dict() or {}
            last_id = data.get("last_id", 0)
            new_id = last_id + 1
            transaction.update(ref, {"last_id": new_id})
        else:
            new_id = 1
            transaction.set(ref, {"last_id": new_id})
        return new_id

    new_number = update_counter(transaction, counter_ref)
    return new_number


import secrets


def ensure_secret_key_exists():
    """
    Key 컬렉션의 'secret' 문서가 없다면,
    랜덤한 키(16바이트 16진수 문자열)를 생성하여 저장하고, 기존 키가 있다면 그대로 반환합니다.
    """
    doc_ref = db.collection("Key").document("secret")

    # 'value' 필드만 가져오고 싶다면 리스트로 전달할 수 있습니다.
    # doc = doc_ref.get(field_paths=["value"])
    # 하지만 전체 문서를 가져오는 것으로도 충분합니다.
    doc = doc_ref.get()  # 인수를 제거하여 전체 문서를 가져옵니다.

    if not doc.exists:
        key = secrets.token_hex(16)
        doc_ref.set({"value": key})
        print("Generated new secret key:", key)
        return key
    else:
        # 문서에서 'value' 필드의 값을 가져옵니다.
        key = doc.get("value")
        print("Existing secret key:", key)
        return key


# 서버 시작 시 secret 키가 DB에 저장되어 있는지 확인
secret_key = ensure_secret_key_exists()
