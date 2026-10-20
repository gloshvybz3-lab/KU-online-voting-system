"""Safe, deterministic navigation assistant for the voting portal.

The MVP intentionally answers from application-owned knowledge instead of
letting a language model invent election state or instructions. A future LLM
provider can be plugged into the same interface for richer natural language.
"""
from models import Election, FAQ


class NavigationAssistant:
    INTENTS = {
        "vote": ("How to vote", "Open My Ballot, choose an active election, review every position, submit your ballot, and keep the receipt code.", "/voting/elections"),
        "elections": ("Elections", "You can view available elections from My Ballot. Only elections currently open or scheduled for you will be shown there.", "/voting/elections"),
        "receipt": ("Verify receipt", "Use Verify Receipt to confirm that your participation was recorded. Your receipt does not reveal your choices.", "/verify-receipt"),
        "register": ("Student registration", "Student voter accounts are created by the Electoral Commission. Contact an administrator to register or update your account.", "/auth/login"),
        "results": ("Election results", "Certified results are published by the Electoral Commission after the results approval step.", "/results"),
        "candidate": ("Candidate information", "Candidate profiles, manifestos, positions and screening status are managed by the Electoral Commission.", "/admin/candidates"),
        "help": ("System help", "I can help you find the ballot, contact the Electoral Commission about registration, verify a receipt, view results, and find candidate information.", None),
    }

    @classmethod
    def respond(cls, message, user=None):
        text = (message or "").strip().lower()
        if not text:
            return {"message": "Ask me where to vote, how to register, how to verify a receipt, where to find results, or how the EC manages candidates.", "links": []}

        if any(k in text for k in ("vote", "ballot", "cast")):
            intent = "vote"
        elif any(k in text for k in ("receipt", "verify my vote", "proof")):
            intent = "receipt"
        elif any(k in text for k in ("register", "registration", "account")):
            intent = "register"
        elif any(k in text for k in ("result", "winner", "tally")):
            intent = "results"
        elif any(k in text for k in ("candidate", "manifesto", "contest")):
            intent = "candidate"
        elif any(k in text for k in ("election", "elections", "poll")):
            intent = "elections"
        else:
            intent = "help"

        title, message, path = cls.INTENTS[intent]
        if intent == "candidate" and user is not None and getattr(user, "is_admin", False):
            path = "/admin/candidates"
        elif intent == "candidate":
            path = "/results"
        links = [{"label": title, "url": path}] if path else []

        # Add current public election information without exposing private data.
        if intent in {"vote", "elections"}:
            current = Election.query.filter(Election.status.in_(["scheduled", "active"])).order_by(Election.start_time.asc()).limit(3).all()
            if current:
                message += " Current elections: " + "; ".join(e.title for e in current) + "."

        return {"message": message, "links": links}
