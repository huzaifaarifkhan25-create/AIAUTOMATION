"""Internal process check, independent of outbound proxy configuration."""
import os
import urllib.request


if __name__ == "__main__":
    host = next((value.strip() for value in os.getenv("APP_ALLOWED_HOSTS", "").split(",") if value.strip()), "127.0.0.1")
    request = urllib.request.Request("http://127.0.0.1:" + os.getenv("PORT", "8000") + "/health", headers={"Host": host})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=3) as response:
        if response.status != 200 or response.read() != b'{"status":"ok"}':
            raise SystemExit("Internal health check failed")
