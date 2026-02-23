from functools import wraps
from flask import session, redirect, url_for

def login_required(view):
    @wraps(view)
    def wrapped(*a, **k):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*a, **k)
    return wrapped

def require_role(role):
    def deco(view):
        @wraps(view)
        def wrapped(*a, **k):
            if session.get("role") != role:
                return redirect(url_for("forbidden"))
            return view(*a, **k)
        return wrapped
    return deco
