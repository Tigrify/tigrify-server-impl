"""User business logic, authorization rules, and profile synchronization."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.core.config import VALID_ROLES
from app.core.serializers import now_utc, serialize_value
from app.repositories.user_repo import UserRepository
from app.schemas.users import UserAddRequest, UserSyncRequest, UserUpdateRequest


def authorize_user_read(ctx: Dict[str, Any], target_uid: str, target_data: Dict[str, Any]) -> None:
    """Enforce owner, Admin, or assigned Parent visibility rules on a user profile."""
    if target_uid == ctx["uid"]:
        return
    if ctx["is_activated"] and ctx["role"] == "ADMIN":
        return
    if ctx["is_activated"] and ctx["role"] == "PARENT" and target_data.get("role") == "STUDENT":
        caller_identifiers = {(ctx["email"] or "").lower().strip(), (ctx["uid"] or "").lower().strip()} - {""}
        if (target_data.get("belongsTo") or "").lower().strip() in caller_identifiers:
            return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to view this user profile.",
    )


class UserService:
    """Service layer for User CRUD, filtering, stats, and token-verified sync."""

    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    def add_user(self, payload: UserAddRequest) -> Dict[str, Any]:
        role = payload.role or "STUDENT"
        if role not in VALID_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{role}'. Must be one of {sorted(VALID_ROLES)}.",
            )

        uid = payload.uid or str(uuid.uuid4())
        if self.repo.get_snapshot(uid).exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with UID {uid} already exists.",
            )

        now = now_utc()
        user_data = {
            "uid": uid,
            "email": payload.email,
            "displayName": (payload.displayName or "User")[:100],
            "role": role,
            "belongsTo": (payload.belongsTo or "ADMIN").strip() or "ADMIN",
            "activated": payload.activated if payload.activated is not None else False,
            "createdAt": now,
            "lastLoginAt": now,
            "loginHistory": [now.isoformat().replace("+00:00", "Z")],
        }
        self.repo.set_user(uid, user_data)
        return {"status": "success", "message": "User created", "user": serialize_value(user_data)}

    def list_users(
        self,
        ctx: Dict[str, Any],
        role: Optional[str] = None,
        belongs_to: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        all_users = self.repo.stream_all()
        users: List[Dict[str, Any]] = []
        search_lower = search.lower().strip() if search else None
        caller_role = ctx["role"]
        caller_identifiers = {
            (ctx["email"] or "").lower().strip(),
            (ctx["uid"] or "").lower().strip(),
            (ctx["profile"].get("displayName") or "").lower().strip(),
        } - {""}

        for u in all_users:
            if caller_role == "PARENT":
                if u.get("role") != "STUDENT":
                    continue
                if (u.get("belongsTo") or "").lower().strip() not in caller_identifiers:
                    continue
            if role and u.get("role") != role:
                continue
            if belongs_to and (u.get("belongsTo", "").lower() != belongs_to.lower()):
                continue
            if search_lower:
                name = (u.get("displayName") or "").lower()
                email = (u.get("email") or "").lower()
                u_role = (u.get("role") or "").lower()
                b_to = (u.get("belongsTo") or "").lower()
                if not (search_lower in name or search_lower in email or search_lower in u_role or search_lower in b_to):
                    continue
            users.append(u)

        return {"status": "success", "count": len(users), "users": users}

    def get_user(
        self, ctx: Dict[str, Any], uid: Optional[str] = None, email: Optional[str] = None
    ) -> Dict[str, Any]:
        if not uid and not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'uid' or 'email' parameter must be provided.",
            )

        if uid:
            u = self.repo.get_or_404(uid)
            authorize_user_read(ctx, u.get("id", uid), u)
            return {"status": "success", "user": u}

        u = self.repo.find_by_email(email or "")
        if not u:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email {email} not found.",
            )
        authorize_user_read(ctx, u.get("id", u.get("uid", "")), u)
        return {"status": "success", "user": u}

    def get_stats(self) -> Dict[str, Any]:
        all_users = self.repo.stream_all()
        total = len(all_users)
        students = sum(1 for u in all_users if u.get("role", "STUDENT") == "STUDENT")
        parents = sum(1 for u in all_users if u.get("role") == "PARENT")
        admins = sum(1 for u in all_users if u.get("role") == "ADMIN")
        return {
            "status": "success",
            "stats": {"total": total, "students": students, "parents": parents, "admins": admins},
        }

    def update_user(self, payload: UserUpdateRequest) -> Dict[str, Any]:
        updates: Dict[str, Any] = {}
        if payload.displayName is not None:
            updates["displayName"] = payload.displayName[:100]
        if payload.role is not None:
            if payload.role not in VALID_ROLES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role '{payload.role}'. Must be one of {sorted(VALID_ROLES)}.",
                )
            updates["role"] = payload.role
        if payload.belongsTo is not None:
            cleaned_belongs = payload.belongsTo.strip()
            if not cleaned_belongs or len(cleaned_belongs) > 254:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="belongsTo must be 1..254 characters.",
                )
            updates["belongsTo"] = cleaned_belongs
        if payload.activated is not None:
            updates["activated"] = payload.activated

        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields specified.")

        updated = self.repo.update_or_404(payload.uid, updates)
        return {"status": "success", "message": "User updated", "user": updated}

    def delete_user(self, uid: str) -> Dict[str, Any]:
        self.repo.delete_or_404(uid)
        return {"status": "success", "message": f"User {uid} deleted."}

    def sync_user(self, payload: UserSyncRequest, decoded: Dict[str, Any]) -> Dict[str, Any]:
        uid = decoded["uid"]
        email = decoded.get("email") or payload.email or ""
        token_name = decoded.get("name") or ""

        doc_ref, doc = self.repo.get_raw_and_ref(uid)
        now = now_utc()
        iso_now = now.isoformat().replace("+00:00", "Z")

        if doc.exists:
            data = doc.to_dict() or {}
            is_activated = bool(decoded.get("email_verified")) or bool(data.get("activated") is True)

            if is_activated and not payload.isRegistration:
                history = data.get("loginHistory") or []
                if not isinstance(history, list):
                    history = []
                history.append(iso_now)
                if len(history) > 500:
                    history = history[-500:]

                updates: Dict[str, Any] = {"lastLoginAt": now, "loginHistory": history}
                chosen_name = (
                    payload.displayName
                    if (payload.displayName and payload.displayName != "Student")
                    else token_name
                )
                if chosen_name:
                    updates["displayName"] = chosen_name[:100]

                doc_ref.update(updates)
                data.update(updates)

            data["uid"] = uid
            return {"status": "success", "isNew": False, "user": serialize_value(data)}

        chosen_name = payload.displayName or token_name or "Student"
        new_user = {
            "uid": uid,
            "email": email,
            "displayName": chosen_name[:100],
            "role": "STUDENT",
            "belongsTo": "ADMIN",
            "activated": False,
            "createdAt": now,
            "lastLoginAt": now,
            "loginHistory": [iso_now],
        }
        doc_ref.set(new_user)
        return {"status": "success", "isNew": True, "user": serialize_value(new_user)}
