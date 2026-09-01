import base64
import io
from typing import Any


def image_to_base64(image: Any, format: str = "PNG", media_type: str | None = None) -> dict[str, str]:
    if hasattr(image, "save"):
        buf = io.BytesIO()
        image.save(buf, format=format)
        b64 = base64.b64encode(buf.getvalue()).decode()
    elif isinstance(image, (bytes, bytearray)):
        b64 = base64.b64encode(bytes(image)).decode()
    else:
        raise TypeError("image must be PIL.Image or bytes")
    mt = media_type or f"image/{format.lower()}"
    return {"image_base64": b64, "media_type": mt}


def bytes_to_response(data: bytes, media_type: str = "image/png"):
    from fastapi.responses import Response

    return Response(content=data, media_type=media_type)
