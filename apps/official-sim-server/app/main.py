from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.router import api_router

app = FastAPI(
    title="Official Sim Server",
    description="Multi-platform official behavior simulation layer for customer service middleware.",
    version="0.1.0",
)

app.include_router(api_router)


@app.get("/healthz")
async def healthz():
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "service": "official-sim-server"}
    )


@app.get("/")
async def root():
    return {"message": "Official Sim Server", "version": "0.1.0"}
