"""Firebase Authentication service and Identity Toolkit / SecureToken REST client."""

from __future__ import annotations

import json
import os
import traceback
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from firebase_admin import auth as firebase_auth
from firebase_functions import logger

from app.core.config import FIREBASE_INIT_URLS
from app.core.firebase import ensure_firebase_initialized
from app.core.serializers import now_utc, serialize_value
from app.repositories.user_repo import UserRepository
from app.schemas.auth import AuthLoginRequest, AuthRefreshRequest, AuthRegisterRequest, AuthVerifyStatusRequest

_CACHED_WEB_API_KEY: Optional[str] = None

_AUTH_ERROR_MAP = {
    "EMAIL_NOT_FOUND": (status.HTTP_401_UNAUTHORIZED, "Invalid email or password."),
    "INVALID_PASSWORD": (status.HTTP_401_UNAUTHORIZED, "Invalid email or password."),
    "INVALID_LOGIN_CREDENTIALS": (status.HTTP_401_UNAUTHORIZED, "Invalid email or password."),
    "USER_DISABLED": (status.HTTP_403_FORBIDDEN, "This account has been disabled."),
    "EMAIL_EXISTS": (status.HTTP_400_BAD_REQUEST, "This email is already registered. Please sign in."),
    "INVALID_EMAIL": (status.HTTP_400_BAD_REQUEST, "Please provide a valid email address."),
    "WEAK_PASSWORD": (status.HTTP_400_BAD_REQUEST, "Password must be at least 6 characters."),
    "TOO_MANY_ATTEMPTS_TRY_LATER": (status.HTTP_429_TOO_MANY_REQUESTS, "Too many attempts. Please try again later."),
    "TOKEN_EXPIRED": (status.HTTP_401_UNAUTHORIZED, "Session expired. Please sign in again."),
    "INVALID_REFRESH_TOKEN": (status.HTTP_401_UNAUTHORIZED, "Invalid refresh token. Please sign in again."),
}


class FirebaseAuthRestClient:
    """HTTP client for Firebase Identity Toolkit & SecureToken REST endpoints."""

    def get_web_api_key(self) -> str:
        global _CACHED_WEB_API_KEY
        env_key = os.environ.get("FIREBASE_WEB_API_KEY")
        if env_key:
            return env_key
        if _CACHED_WEB_API_KEY:
            return _CACHED_WEB_API_KEY
        for url in FIREBASE_INIT_URLS:
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("apiKey"):
                        _CACHED_WEB_API_KEY = data["apiKey"]
                        logger.info("Discovered Firebase Web API key from init.json", url=url)
                        return _CACHED_WEB_API_KEY
            except Exception as exc:
                logger.warn("Failed fetching Firebase init.json", url=url, errorType=type(exc).__name__, error=str(exc))
        logger.error("FIREBASE_WEB_API_KEY lookup failed across all init.json URLs")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="FIREBASE_WEB_API_KEY is not configured and could not be auto-discovered.",
        )

    def post(self, url: str, payload: Any, form_encoded: bool = False) -> Dict[str, Any]:
        if form_encoded:
            body = urllib.parse.urlencode(payload).encode("utf-8")
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
        else:
            body = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json"}

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            raw = err.read().decode("utf-8", errors="ignore")
            err_code = ""
            try:
                err_code = ((json.loads(raw).get("error") or {}).get("message")) or ""
            except Exception:
                pass
            logger.warn("Firebase Auth REST HTTP error", statusCode=err.code, errorCode=err_code)
            base_code = err_code.split(":")[0].strip()
            http_code, friendly = _AUTH_ERROR_MAP.get(
                base_code, (status.HTTP_400_BAD_REQUEST, err_code or "Authentication request failed.")
            )
            raise HTTPException(status_code=http_code, detail=friendly)
        except Exception as exc:
            logger.error(
                "Firebase Auth REST network/request failure",
                errorType=type(exc).__name__,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Firebase Auth upstream error: {type(exc).__name__}: {exc}",
            )


class AuthService:
    """Authentication workflows backed by Firebase Auth and UserRepository."""

    def __init__(
        self,
        user_repo: UserRepository,
        rest_client: Optional[FirebaseAuthRestClient] = None,
        auth_sdk: Any = firebase_auth,
    ) -> None:
        self.user_repo = user_repo
        self.rest = rest_client or FirebaseAuthRestClient()
        self.auth_sdk = auth_sdk

    def register(self, payload: AuthRegisterRequest) -> Dict[str, Any]:
        ensure_firebase_initialized()
        email = payload.email.strip()
        full_name = payload.fullName.strip()

        try:
            user_record = self.auth_sdk.create_user(
                email=email,
                password=payload.password,
                display_name=full_name,
            )
        except self.auth_sdk.EmailAlreadyExistsError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email is already registered. Please sign in.",
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        uid = user_record.uid
        now = now_utc()
        iso_now = now.isoformat().replace("+00:00", "Z")
        new_user = {
            "uid": uid,
            "email": email,
            "displayName": full_name[:100],
            "role": "STUDENT",
            "belongsTo": "ADMIN",
            "activated": False,
            "createdAt": now,
            "lastLoginAt": now,
            "loginHistory": [iso_now],
        }
        self.user_repo.set_user(uid, new_user)

        api_key = self.rest.get_web_api_key()
        auth_resp = self.rest.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}",
            {"email": email, "password": payload.password, "returnSecureToken": True},
        )
        id_token = auth_resp.get("idToken")
        refresh_token = auth_resp.get("refreshToken")

        if id_token:
            self.rest.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}",
                {"requestType": "VERIFY_EMAIL", "idToken": id_token},
            )

        return {
            "status": "success",
            "message": "Account registered! A verification link has been sent to your email.",
            "activated": False,
            "emailVerified": False,
            "idToken": id_token,
            "refreshToken": refresh_token,
            "user": serialize_value(new_user),
        }

    def login(self, payload: AuthLoginRequest) -> Dict[str, Any]:
        api_key = self.rest.get_web_api_key()
        auth_resp = self.rest.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}",
            {"email": payload.email.strip(), "password": payload.password, "returnSecureToken": True},
        )

        id_token = auth_resp["idToken"]
        refresh_token = auth_resp["refreshToken"]
        expires_in = auth_resp.get("expiresIn", "3600")

        ensure_firebase_initialized()
        decoded = self.auth_sdk.verify_id_token(id_token)
        uid = decoded["uid"]
        email = decoded.get("email") or payload.email.strip()
        email_verified = bool(decoded.get("email_verified"))

        doc_ref, doc = self.user_repo.get_raw_and_ref(uid)
        now = now_utc()
        iso_now = now.isoformat().replace("+00:00", "Z")

        if doc.exists:
            user_data = doc.to_dict() or {}
        else:
            user_data = {
                "uid": uid,
                "email": email,
                "displayName": (decoded.get("name") or auth_resp.get("displayName") or "Student")[:100],
                "role": "STUDENT",
                "belongsTo": "ADMIN",
                "activated": False,
                "createdAt": now,
                "lastLoginAt": now,
                "loginHistory": [iso_now],
            }
            doc_ref.set(user_data)

        is_activated = email_verified or bool(user_data.get("activated") is True)
        if not is_activated:
            user_data["uid"] = uid
            return {
                "status": "verification_required",
                "message": "Your account is not activated yet. Please verify your email or ask an admin to activate it.",
                "activated": False,
                "emailVerified": False,
                "idToken": id_token,
                "refreshToken": refresh_token,
                "expiresIn": expires_in,
                "user": serialize_value(user_data),
            }

        history = user_data.get("loginHistory") or []
        if not isinstance(history, list):
            history = []
        history.append(iso_now)
        if len(history) > 500:
            history = history[-500:]

        doc_ref.update({"lastLoginAt": now, "loginHistory": history})
        user_data["lastLoginAt"] = now
        user_data["loginHistory"] = history
        user_data["uid"] = uid

        return {
            "status": "success",
            "message": "Signed in successfully.",
            "activated": True,
            "emailVerified": email_verified,
            "idToken": id_token,
            "refreshToken": refresh_token,
            "expiresIn": expires_in,
            "user": serialize_value(user_data),
        }

    def refresh(self, payload: AuthRefreshRequest) -> Dict[str, Any]:
        api_key = self.rest.get_web_api_key()
        resp = self.rest.post(
            f"https://securetoken.googleapis.com/v1/token?key={api_key}",
            {"grant_type": "refresh_token", "refresh_token": payload.refreshToken},
            form_encoded=True,
        )
        return {
            "status": "success",
            "idToken": resp["id_token"],
            "refreshToken": resp["refresh_token"],
            "expiresIn": resp.get("expires_in", "3600"),
        }

    def me(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        profile = dict(ctx["profile"])
        if profile:
            profile["uid"] = ctx["uid"]
        return {
            "status": "success",
            "uid": ctx["uid"],
            "email": ctx["email"],
            "emailVerified": bool(ctx["decoded"].get("email_verified")),
            "isActivated": ctx["is_activated"],
            "role": ctx["role"],
            "user": serialize_value(profile) if profile else None,
        }

    def resend_verification(self, id_token: str) -> Dict[str, Any]:
        api_key = self.rest.get_web_api_key()
        self.rest.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}",
            {"requestType": "VERIFY_EMAIL", "idToken": id_token},
        )
        return {"status": "success", "message": "New verification link sent! Please check your inbox."}

    def check_verification_status(
        self, payload: AuthVerifyStatusRequest, decoded: Dict[str, Any]
    ) -> Dict[str, Any]:
        ensure_firebase_initialized()
        uid = decoded["uid"]
        user_record = self.auth_sdk.get_user(uid)
        email_verified = bool(user_record.email_verified)

        _, doc = self.user_repo.get_raw_and_ref(uid)
        user_data = doc.to_dict() if doc.exists else {}
        db_activated = bool((user_data or {}).get("activated") is True)
        is_activated = email_verified or db_activated

        new_id_token = None
        new_refresh_token = None
        if is_activated and payload.refreshToken:
            try:
                api_key = self.rest.get_web_api_key()
                refreshed = self.rest.post(
                    f"https://securetoken.googleapis.com/v1/token?key={api_key}",
                    {"grant_type": "refresh_token", "refresh_token": payload.refreshToken},
                    form_encoded=True,
                )
                new_id_token = refreshed.get("id_token")
                new_refresh_token = refreshed.get("refresh_token")
            except Exception:
                pass

        if user_data:
            user_data["uid"] = uid

        return {
            "status": "success",
            "emailVerified": email_verified,
            "activated": db_activated,
            "isActivated": is_activated,
            "idToken": new_id_token,
            "refreshToken": new_refresh_token,
            "user": serialize_value(user_data) if user_data else None,
        }
