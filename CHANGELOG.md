# Changelog

## 0.1.7 - 2026-09-01
- **Security:** RateLimit 429 handler, WS X-API-Key auth, file size via Content-Length+bytes, CORS `*` no credentials, payload 1MB limit, file-type warning
- **Server:** Pure ASGI LoggingMiddleware (no SSE buffering), GZip 1000, lifespan timeout 120s for run+stream, real metrics `request_count`
- **Config:** `INFERKIT_` prefix + plain `HOST/PORT` AliasChoices, CORS JSON/comma/*, `get_settings()` cache
- **DX:** `image_to_base64`/`bytes_to_response` helpers, 1-file `my_model.py` via `inferkit init`, sync/async `@infer` + `@infer.stream`
- **CLI:** `sys.path` fix, single-worker deploy (no model missing), `requirements.txt` aware, dynamic `HOST/PORT`
- **Packaging:** `Pillow` → `vision` optional, classifiers, `Issues/Changelog` URLs
- **Tests:** 22 tests, coverage 66%, conftest isolation, security tests for 429/401/413/CORS
- **Docs:** Full `index.md` + `api.md` with curl/WS examples

## 0.1.6 - 2024
- Pillow optional, helpers, middleware fix

## 0.1.5 - 2024
- Tests 14, coverage 62%, mypy, ruff
- Dependabot, CodeQL, MkDocs GH Pages
- Lifespan preload for large models

## 0.1.4 - 2024
- Coverage/mypy/docs/lifespan

## 0.1.3 - 2024
- Sync support, logging/metrics, bump CLI, optional deps

## 0.1.2 - 2024
- Initial stable release, auto publish via GitHub Actions

## 0.1.0 - 0.1.1
- Early builds
