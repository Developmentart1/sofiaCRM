"""User routes — auth + CRUD."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from core.audit import audit_log
from core.config import get_settings
from core.rbac import Permission, require_permission
from modules.users.auth_deps import CurrentUser, get_current_user, get_db_session
from modules.users.schemas import (
    LoginRequest, CompanyLoginRequest, LoginResponse, UserCreate, UserPasswordChange, UserRead,
)
from modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])

ACCESS_TOKEN_COOKIE = "access_token"


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db_session),
) -> LoginResponse:
    result = UserService(db).login(payload)
    settings = get_settings()
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=result.access_token,
        httponly=True,
        samesite="lax",
        secure=settings.env not in ("development", "test"),
        max_age=settings.jwt_expire_minutes * 60,
    )
    return result


@router.post("/login/company", response_model=LoginResponse)
def login_company(
    payload: CompanyLoginRequest,
    response: Response,
    db: Session = Depends(get_db_session),
) -> LoginResponse:
    result = UserService(db).login_company(payload.organization_slug, payload.password)
    settings = get_settings()
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=result.access_token,
        httponly=True,
        samesite="lax",
        secure=settings.env not in ("development", "test"),
        max_age=settings.jwt_expire_minutes * 60,
    )
    return result


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(ACCESS_TOKEN_COOKIE)
    return {"detail": "ok"}


@router.get("/me", response_model=UserRead)
def me(current: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db_session)) -> UserRead:
    return UserService(db).get(current.id)


@router.post("/me/password")
def change_my_password(
    payload: UserPasswordChange,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> dict[str, str]:
    UserService(db).change_password(current.id, current=payload.current_password, new=payload.new_password)
    return {"detail": "ok"}


@router.get("", response_model=list[UserRead])
@audit_log("user.list")
def list_users(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[UserRead]:
    require_permission(current.role, Permission.USER_READ)
    return UserService(db).list_all(current.organization_id)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@audit_log("user.create")
def create_user(
    payload: UserCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> UserRead:
    require_permission(current.role, Permission.USER_CREATE)
    return UserService(db).create(payload)
