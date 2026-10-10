# Google Stitch design connection

Stitch is a design tool for Codex. It is separate from the Gemini API used for app drafts, and neither replaces the Google Maps collector. This repository contains a key-free project MCP configuration in `.codex/config.toml`.

The key shown in the chat screenshot has been exposed. Revoke or rotate it in Google Stitch before use. Set the replacement only in a private shell environment as `STITCH_API_KEY`, then restart Codex in this project. Codex should load the Stitch MCP server at `https://stitch.googleapis.com/mcp` and send the key in `X-Goog-Api-Key`. The current session has no `STITCH_API_KEY`, so a live connection has not been verified.

The supplied dashboard screenshot is a visual reference only. The new frontend uses AIAutomation branding, saved CRM data, and its own components. The other supplied screenshot contains a secret and is deliberately excluded from design assets.

Google source: [Stitch MCP design workflow](https://codelabs.developers.google.com/design-to-code-with-antigravity-stitch), [Stitch MCP endpoint](https://docs.cloud.google.com/mcp/supported-products).
