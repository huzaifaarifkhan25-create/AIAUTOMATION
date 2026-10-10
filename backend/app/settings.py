import os
import re
import ipaddress
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    app_allowed_hosts: tuple[str, ...] = ()
    app_public_url: str = ""
    app_api_token: str = field(default="", repr=False)
    persistence_backend: str = "sqlite"
    database_path: str = str(Path(__file__).resolve().parents[2] / ".local/backend.sqlite3")
    google_places_api_key: str = field(default="", repr=False)
    llm_api_key: str = field(default="", repr=False)
    llm_model: str = "gpt-4.1-mini"
    gemini_api_key: str = field(default="", repr=False)
    gemini_model: str = "gemini-3.5-flash"
    supabase_url: str = ""
    supabase_key: str = field(default="", repr=False)
    website_allowed_hosts: tuple[str, ...] = ()
    website_dns_over_https: bool = False
    website_follow_redirects: bool = False
    twilio_account_sid: str = ""
    twilio_auth_token: str = field(default="", repr=False)
    twilio_from_number: str = ""
    sales_agent_number: str = ""
    enable_outbound_calls: bool = False
    enable_email_delivery: bool = False
    resend_api_key: str = field(default="", repr=False)
    resend_from_email: str = ""
    resend_webhook_secret: str = field(default="", repr=False)
    browser_runtime: str = "local" if os.name == "nt" else "docker"
    scrape_output_path: str = str(Path(__file__).resolve().parents[2] / ".local/scrapes")

    def validate_runtime(self):
        if self.app_env not in {"development", "production"}:
            raise ValueError("APP_ENV must be development or production")
        if self.browser_runtime not in {"docker", "local"}:
            raise ValueError("BROWSER_RUNTIME must be docker or local")
        if self.app_public_url:
            parsed = urlsplit(self.app_public_url)
            try:
                public_address = ipaddress.ip_address(parsed.hostname).is_global
            except ValueError:
                public_address = True
            if (parsed.scheme != "https" or not parsed.hostname or "." not in parsed.hostname
                or not public_address or parsed.hostname.endswith(".localhost") or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.path not in {"", "/"} or parsed.port not in {None, 443}
                or not re.fullmatch(r"[a-z0-9.-]+", parsed.hostname)
                or (self.app_env == "production" and parsed.hostname not in self.app_allowed_hosts)):
                raise ValueError("APP_PUBLIC_URL must be the actual HTTPS app origin with an allowed hostname")
        if self.app_env == "production":
            if len(self.app_api_token) < 32 or self.app_api_token.isspace() or any(ord(c) < 33 or ord(c) > 126 for c in self.app_api_token):
                raise ValueError("Production requires APP_API_TOKEN with at least 32 printable non-space characters")
            if not self.app_allowed_hosts or any(len(host) > 253 or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*", host)
                or any(len(label) > 63 for label in host.split(".")) for host in self.app_allowed_hosts):
                raise ValueError("Production requires APP_ALLOWED_HOSTS with explicit hostnames, without schemes or ports")

    @classmethod
    def from_env(cls):
        defaults = cls()
        backend = os.getenv("PERSISTENCE_BACKEND", "sqlite")
        if backend not in {"sqlite", "supabase"}:
            raise ValueError("PERSISTENCE_BACKEND must be sqlite or supabase")
        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            app_public_url=os.getenv("APP_PUBLIC_URL", "").rstrip("/"),
            app_allowed_hosts=tuple(host.strip().lower() for host in os.getenv("APP_ALLOWED_HOSTS", "").split(",") if host.strip()),
            app_api_token=os.getenv("APP_API_TOKEN", ""),
            persistence_backend=backend,
            database_path=os.getenv("APP_DB_PATH", defaults.database_path),
            google_places_api_key=os.getenv("GOOGLE_PLACES_API_KEY", ""),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", defaults.llm_model),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            gemini_model=os.getenv("GEMINI_MODEL", defaults.gemini_model),
            supabase_url=os.getenv("SUPABASE_URL", "").rstrip("/"),
            supabase_key=os.getenv("SUPABASE_KEY", ""),
            website_allowed_hosts=tuple(
                host.strip().lower() for host in os.getenv("WEBSITE_ALLOWED_HOSTS", "").split(",")
                if host.strip()
            ),
            website_dns_over_https=os.getenv("WEBSITE_DNS_OVER_HTTPS", "false").lower() == "true",
            website_follow_redirects=os.getenv("WEBSITE_FOLLOW_REDIRECTS", "false").lower() == "true",
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            twilio_from_number=os.getenv("TWILIO_FROM_NUMBER", ""),
            sales_agent_number=os.getenv("SALES_AGENT_NUMBER", ""),
            enable_outbound_calls=os.getenv("ENABLE_OUTBOUND_CALLS", "false").lower() == "true",
            enable_email_delivery=os.getenv("ENABLE_EMAIL_DELIVERY", "false").lower() == "true",
            resend_api_key=os.getenv("RESEND_API_KEY", ""),
            resend_from_email=os.getenv("RESEND_FROM_EMAIL", ""),
            resend_webhook_secret=os.getenv("RESEND_WEBHOOK_SECRET", ""),
            browser_runtime=os.getenv("BROWSER_RUNTIME", defaults.browser_runtime),
            scrape_output_path=os.getenv("SCRAPE_OUTPUT_DIR", defaults.scrape_output_path),
        )
