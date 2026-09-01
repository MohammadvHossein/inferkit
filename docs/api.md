# API Reference

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/` | - | خوش‌آمد + `has_model` |
| `GET` | `/health` | - | سلامت |
| `GET` | `/metrics` | - | `{"requests": int, "model_loaded": bool}` |
| `GET` | `/api/v1/info` | - | اطلاعات مدل |
| `POST` | `/api/v1/infer` | `X-API-Key` اگر ست باشد | `multipart/form-data`: `payload` (JSON string) + `files` (چند فایل). محدودیت `413` |
| `POST` | `/api/v1/infer/json` | `X-API-Key` | `application/json` بدنه JSON. محدودیت `1MB` |
| `POST` | `/api/v1/infer/stream` | `X-API-Key` | SSE `text/event-stream`: `data: {"token": ...}` + `data: [DONE]` |
| `WS` | `/ws/infer` | `X-API-Key` header یا `?api_key=` | WebSocket: ارسال `{"text":"hi"}` یا `{"text":"hi","stream":true}`، دریافت `{"output":...}` یا `{"token":...}` + `{"done":true}` |
| `WS` | `/api/v1/ws/infer` | همان | Alias برای WS |

## مثال curl

```bash
# JSON
curl -X POST http://localhost:8000/api/v1/infer/json -H "Content-Type: application/json" -d '{"text":"hello"}'

# فایل
curl -X POST http://localhost:8000/api/v1/infer -F payload='{"text":"hi"}' -F files=@cat.jpg

# SSE
curl -N -X POST http://localhost:8000/api/v1/infer/stream -H "Content-Type: application/json" -d '{"text":"hello world"}'

# WS (wscat)
wscat -c ws://localhost:8000/ws/infer
> {"text":"hello","stream":true}
< {"token":"hello "}
```

## خطاها
- `400` JSON نامعتبر یا `payload` غیر-object
- `401` API key اشتباه
- `413` حجم payload/فایل بیش از حد
- `429` Rate limit (`60/minute` پیش‌فرض)
- `500` مدل ثبت نشده یا خطای inference (در `DEBUG=false` پیام عمومی)

## Rate Limit
هدر `X-API-Key` + `slowapi` با `INFERKIT_RATE_LIMIT`. پاسخ `429 {"error":"rate limit exceeded"}`

## CORS
`INFERKIT_CORS_ORIGINS=["*"]` → `allow_credentials=False` (خودکار). برای دامنه خاص: `["http://a.com"]` → `allow_credentials=True`
