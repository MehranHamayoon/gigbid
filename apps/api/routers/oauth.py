import os
from base64 import urlsafe_b64encode
from hashlib import sha256
from secrets import token_urlsafe
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from apps.api.auth import oauth_store
from apps.api.auth.session import user

router = APIRouter(prefix="/oauth/upwork", tags=["OAuth"])


def configured():
    required = ("UPWORK_CLIENT_ID", "UPWORK_AUTHORIZE_URL", "UPWORK_TOKEN_URL", "UPWORK_REDIRECT_URI", "APP_SECRET_KEY")
    values = {key: os.getenv(key) for key in required}
    if not all(values.values()):
        raise HTTPException(503, "Upwork OAuth is awaiting registered client configuration")
    for key in ("UPWORK_AUTHORIZE_URL", "UPWORK_TOKEN_URL"):
        url = urlparse(values[key])
        if url.scheme != "https" or not (url.hostname == "upwork.com" or (url.hostname or "").endswith(".upwork.com")):
            raise HTTPException(503, "Use the official Upwork OAuth endpoints")
    return values


@router.get("/start")
def start(account=Depends(user)):
    values = configured()
    verifier = token_urlsafe(48)
    state = token_urlsafe(32)
    challenge = urlsafe_b64encode(sha256(verifier.encode()).digest()).decode().rstrip("=")
    params = {"client_id": values["UPWORK_CLIENT_ID"], "redirect_uri": values["UPWORK_REDIRECT_URI"],
              "response_type": "code", "code_challenge_method": "S256", "code_challenge": challenge, "state": state}
    response = RedirectResponse(values["UPWORK_AUTHORIZE_URL"] + "?" + urlencode(params))
    encrypted = oauth_store.cipher().encrypt(f'{account["id"]}:{state}:{verifier}'.encode()).decode()
    response.set_cookie("gb_oauth", encrypted, max_age=600, httponly=True, secure=os.getenv("APP_ENV") == "production",
                        samesite="lax", path="/api/oauth/upwork")
    return response


@router.get("/callback")
async def callback(request: Request, code: str, state: str, account=Depends(user)):
    values = configured()
    try:
        stored = request.cookies["gb_oauth"]
        user_id, expected, verifier = oauth_store.cipher().decrypt(stored.encode(), ttl=600).decode().split(":")
    except Exception as exc:
        raise HTTPException(400, "OAuth state is invalid or expired") from exc
    if user_id != account["id"] or expected != state:
        raise HTTPException(400, "OAuth state mismatch")
    payload = {"grant_type": "authorization_code", "code": code, "code_verifier": verifier,
               "client_id": values["UPWORK_CLIENT_ID"], "redirect_uri": values["UPWORK_REDIRECT_URI"]}
    if os.getenv("UPWORK_CLIENT_SECRET"):
        payload["client_secret"] = os.environ["UPWORK_CLIENT_SECRET"]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(values["UPWORK_TOKEN_URL"], data=payload)
            response.raise_for_status()
            token = response.json()["access_token"]
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise HTTPException(502, "Upwork rejected the authorization exchange") from exc
    oauth_store.save(user_id, token)
    redirect = RedirectResponse("/settings")
    redirect.delete_cookie("gb_oauth", path="/api/oauth/upwork")
    return redirect
