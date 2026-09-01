from inferkit import infer

@infer
async def run(payload, files=None):
    if not files:
        return {"error": "no audio"}
    return {"transcript": "hello world", "bytes": len(files[0])}

@infer.stream
async def run_stream(payload):
    text = payload.get("text", "")
    for w in text.split():
        yield w + " "
