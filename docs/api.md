# API Reference

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/` | - | Welcome + `has_model` |
| `GET` | `/health` | - | Health check |
| `GET` | `/metrics` | - | `{"requests": int, "model_loaded": bool}` |
| `GET` | `/api/v1/info` | - | Model info |
| `POST` | `/api/v1/infer` | `X-API-Key` if set | `multipart/form-data`: `payload` (JSON string) + `files` (multiple files). Limit `413` |
| `POST` | `/api/v1/infer/json` | `X-API-Key` | `application/json` body. Limit `1MB` |
| `POST` | `/api/v1/infer/stream` | `X-API-Key` | SSE `text/event-stream`: `data: {"token": ...}` + `data: [DONE]` |
| `WS` | `/ws/infer` | `X-API-Key` header or `?api_key=` | WebSocket: send `{"text":"hi"}` or `{"text":"hi","stream":true}`, receive `{"output":...}` or `{"token":...}` + `{"done":true}` |
| `WS` | `/api/v1/ws/infer` | same | Alias for WS |

## curl Examples

```bash
# JSON
curl -X POST http://localhost:8000/api/v1/infer/json -H "Content-Type: application/json" -d '{"text":"hello"}'

# File
curl -X POST http://localhost:8000/api/v1/infer -F payload='{"text":"hi"}' -F files=@cat.jpg

# SSE
curl -N -X POST http://localhost:8000/api/v1/infer/stream -H "Content-Type: application/json" -d '{"text":"hello world"}'

# WS (wscat)
wscat -c ws://localhost:8000/ws/infer
> {"text":"hello","stream":true}
< {"token":"hello "}
```

## Errors
- `400` Invalid JSON or `payload` not an object
- `401` Invalid API key
- `413` Payload/file too large
- `429` Rate limit (`60/minute` default)
- `500` No model registered or inference error (generic message when `DEBUG=false`)

## Rate Limit
Uses `slowapi` with `INFERKIT_RATE_LIMIT`. Response `429 {"error":"rate limit exceeded"}`

## CORS
`INFERKIT_CORS_ORIGINS=["*"]` -> `allow_credentials=False` (automatic). For specific domain: `["http://a.com"]` -> `allow_credentials=True`
