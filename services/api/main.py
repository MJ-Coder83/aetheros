from fastapi import FastAPI

from packages.tape.models import TapeEntry

app = FastAPI(title="AetherOS API")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/tape/log")
async def log_event(entry: TapeEntry):
    return {"status": "logged", "id": str(entry.id)}
