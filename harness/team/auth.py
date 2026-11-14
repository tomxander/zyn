"""Authentication and identity providers for team mode."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, TypedDict

from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

if TYPE_CHECKING:
    from harness.team.settings import OidcSettings


class Claims(TypedDict):
    sub: str
    iss: str
    name: str
    email: str | None
    groups: list[str]


class IdentityProvider(Protocol):
    async def login_redirect(self, request: Request) -> Response: ...
    async def callback(self, request: Request) -> Claims: ...


class FakeIdentityProvider:
    """In-memory identity provider for tests."""

    def __init__(self, claims: Claims):
        self.claims = claims

    async def login_redirect(self, request: Request) -> Response:
        return RedirectResponse(url="/auth/callback", status_code=303)

    async def callback(self, request: Request) -> Claims:
        return self.claims


class OidcProvider:
    """OpenID Connect provider using Authlib."""

    def __init__(self, settings: OidcSettings, public_url: str):
        self.settings = settings
        self.public_url = public_url.rstrip("/")

        from authlib.integrations.starlette_client import OAuth

        self.oauth = OAuth()
        meta_url = (settings.internal_url or settings.issuer).rstrip("/") + "/.well-known/openid-configuration"
        self.oauth.register(
            name="oidc",
            server_metadata_url=meta_url,
            client_id=settings.client_id,
            client_secret=settings.client_secret,
            client_kwargs={
                "scope": " ".join(settings.scopes),
                "code_challenge_method": "S256",
            },
        )

    async def login_redirect(self, request: Request) -> Response:
        redirect_uri = f"{self.public_url}/auth/callback"
        resp = await self.oauth.oidc.authorize_redirect(request, redirect_uri)
        if self.settings.internal_url and "location" in resp.headers:
            loc = resp.headers["location"]
            internal_base = self.settings.internal_url.rstrip("/")
            issuer_base = self.settings.issuer.rstrip("/")
            if loc.startswith(internal_base):
                resp.headers["location"] = loc.replace(internal_base, issuer_base, 1)
        return resp

    async def callback(self, request: Request) -> Claims:
        if self.settings.internal_url:
            meta = await self.oauth.oidc.load_server_metadata()
            issuer_base = self.settings.issuer.rstrip("/")
            internal_base = self.settings.internal_url.rstrip("/")
            for k in ("token_endpoint", "userinfo_endpoint", "jwks_uri"):
                if k in meta and meta[k].startswith(issuer_base):
                    meta[k] = meta[k].replace(issuer_base, internal_base, 1)
        token = await self.oauth.oidc.authorize_access_token(request)
        userinfo = token.get("userinfo") or await self.oauth.oidc.userinfo(token=token)
        groups_claim = self.settings.groups_claim
        groups = userinfo.get(groups_claim, [])
        if isinstance(groups, str):
            groups = [groups]
        return Claims(
            sub=str(userinfo.get("sub", "")),
            iss=str(userinfo.get("iss", self.settings.issuer)),
            name=str(userinfo.get("name") or userinfo.get("preferred_username") or userinfo.get("sub", "")),
            email=userinfo.get("email"),
            groups=list(groups),
        )
