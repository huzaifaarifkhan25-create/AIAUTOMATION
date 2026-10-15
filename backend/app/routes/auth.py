from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.errors import AppError
from app.services.auth import SESSION_SECONDS

router = APIRouter(prefix="/auth", tags=["Accounts"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128, repr=False)

    @field_validator("email")
    @classmethod
    def email_address(cls, value):
        value = value.strip().lower()
        local, separator, domain = value.partition("@")
        if not separator or not local or "." not in domain or "@" in domain or any(c.isspace() or ord(c) < 33 for c in value) or not value.isascii():
            raise ValueError("Enter a valid email address")
        return value


class RegisterRequest(LoginRequest):
    password: str = Field(min_length=12, max_length=128, repr=False)
    name: str = Field(min_length=1, max_length=80)
    access_code: str = Field(default="", max_length=512, repr=False)
    confirm_shared_workspace: bool

    @field_validator("confirm_shared_workspace", mode="before")
    @classmethod
    def confirmation(cls, value):
        if value is not True:
            raise ValueError("Confirm that this account joins the shared workspace")
        return value

    @field_validator("name", "password")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("This field cannot be blank")
        return value


def same_origin(request):
    origin = request.headers.get("origin")
    if origin:
        parsed = urlsplit(origin)
        allowed = {str(request.base_url).rstrip("/")}
        if request.app.state.settings.app_public_url:
            allowed.add(request.app.state.settings.app_public_url.rstrip("/"))
        if origin not in allowed or parsed.scheme not in {"http", "https"}:
            raise AppError(403, "auth_origin_rejected", "Use the sign-in form on this server")
    if request.headers.get("sec-fetch-site") not in {None, "same-origin", "none"}:
        raise AppError(403, "auth_origin_rejected", "Use the sign-in form on this server")


def signed_in(request, result, status=200):
    user, token = result
    from app.services.auth import digest
    response = JSONResponse({"user": user, "csrf_token": digest(token + ":csrf"), "workspace": "shared"}, status_code=status)
    accounts = request.app.state.accounts
    response.set_cookie(accounts.cookie, token, max_age=SESSION_SECONDS, httponly=True,
                        secure=request.app.state.settings.app_env == "production", samesite="strict", path="/")
    return response


@router.get("/status")
async def status(request: Request):
    return await request.app.state.accounts.status(request)


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, request: Request):
    same_origin(request)
    return signed_in(request, await request.app.state.accounts.register(request, body), 201)


@router.post("/login")
async def login(body: LoginRequest, request: Request):
    same_origin(request)
    return signed_in(request, await request.app.state.accounts.login(request, body))


@router.get("/me")
async def me(request: Request):
    return {**await request.app.state.accounts.session(request), "workspace": "shared"}


@router.post("/logout")
async def logout(request: Request):
    same_origin(request)
    await request.app.state.accounts.logout(request)
    response = JSONResponse({"signed_out": True})
    response.delete_cookie(request.app.state.accounts.cookie, path="/", secure=request.app.state.settings.app_env == "production", httponly=True, samesite="strict")
    return response
