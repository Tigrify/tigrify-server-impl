"""User CRUD and synchronization endpoints (/api/user/*)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.core.firebase import get_db
from app.core.security import get_caller_context, require_admin, require_parent_or_admin, verify_token
from app.repositories.user_repo import UserRepository
from app.schemas.users import UserAddRequest, UserDeleteRequest, UserSyncRequest, UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter()


def get_user_service(db: Any = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))


@router.post("/user/add", tags=["Users"], summary="Add / Create a new User (Admin only)")
@router.post("/users", tags=["Users"], include_in_schema=False)
def add_user(
    payload: UserAddRequest,
    ctx: Dict[str, Any] = Depends(require_admin),
    service: UserService = Depends(get_user_service),
):
    return service.add_user(payload)


@router.get("/user/list", tags=["Users"], summary="List Users (Admin: all; Parent: assigned students only)")
@router.get("/users", tags=["Users"], include_in_schema=False)
def list_users(
    role: Optional[str] = Query(None, description="Filter by role (STUDENT, PARENT, OPERATOR, ADMIN)"),
    belongsTo: Optional[str] = Query(None, description="Filter by belongsTo account email or UID"),
    search: Optional[str] = Query(None, description="Filter by searching in displayName, email, role, or belongsTo"),
    ctx: Dict[str, Any] = Depends(require_parent_or_admin),
    service: UserService = Depends(get_user_service),
):
    return service.list_users(ctx, role=role, belongs_to=belongsTo, search=search)


@router.get("/user/get", tags=["Users"], summary="Get User Profile by UID or Email")
def get_user_query(
    uid: Optional[str] = Query(None, description="Firebase Auth UID of the user"),
    email: Optional[str] = Query(None, description="Email address of the user"),
    ctx: Dict[str, Any] = Depends(get_caller_context),
    service: UserService = Depends(get_user_service),
):
    return service.get_user(ctx, uid=uid, email=email)


@router.get("/user/stats", tags=["Users"], summary="Get User Statistics Summary (Admin only)")
def get_user_stats(
    ctx: Dict[str, Any] = Depends(require_admin),
    service: UserService = Depends(get_user_service),
):
    return service.get_stats()


@router.get("/user/{uid}", tags=["Users"], summary="Get User by UID path")
def get_user_by_path(
    uid: str,
    ctx: Dict[str, Any] = Depends(get_caller_context),
    service: UserService = Depends(get_user_service),
):
    return service.get_user(ctx, uid=uid)


@router.post("/user/update", tags=["Users"], summary="Update User Details (Admin only)")
@router.put("/user/update", tags=["Users"], include_in_schema=False)
def update_user(
    payload: UserUpdateRequest,
    ctx: Dict[str, Any] = Depends(require_admin),
    service: UserService = Depends(get_user_service),
):
    return service.update_user(payload)


@router.put("/user/{uid}", tags=["Users"], include_in_schema=False)
def update_user_path(
    uid: str,
    payload: UserUpdateRequest,
    ctx: Dict[str, Any] = Depends(require_admin),
    service: UserService = Depends(get_user_service),
):
    payload.uid = uid
    return service.update_user(payload)


@router.post("/user/delete", tags=["Users"], summary="Delete a User Profile (Admin only)")
@router.delete("/user/delete", tags=["Users"], include_in_schema=False)
def delete_user(
    payload: UserDeleteRequest,
    ctx: Dict[str, Any] = Depends(require_admin),
    service: UserService = Depends(get_user_service),
):
    return service.delete_user(payload.uid)


@router.delete("/user/{uid}", tags=["Users"], include_in_schema=False)
def delete_user_path(
    uid: str,
    ctx: Dict[str, Any] = Depends(require_admin),
    service: UserService = Depends(get_user_service),
):
    return service.delete_user(uid)


@router.post("/user/sync", tags=["Users"], summary="Synchronize Authenticated User Profile")
def sync_user(
    payload: UserSyncRequest,
    decoded: Dict[str, Any] = Depends(verify_token),
    service: UserService = Depends(get_user_service),
):
    return service.sync_user(payload, decoded)
