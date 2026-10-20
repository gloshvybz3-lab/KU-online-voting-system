from flask import Blueprint, jsonify, request
from flask_login import current_user
from services.chatbot_service import NavigationAssistant

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


@api_bp.post("/assistant/chat")
def assistant_chat():
    payload = request.get_json(silent=True) or {}
    message = payload.get("message", "")
    if not isinstance(message, str) or len(message) > 1000:
        return jsonify({"error": "Message must be a string of at most 1000 characters."}), 400
    result = NavigationAssistant.respond(message, current_user if current_user.is_authenticated else None)
    return jsonify({"ok": True, **result})


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})
