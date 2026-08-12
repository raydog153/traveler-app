from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import dashboard, gas, maintenance, map as map_router

app = FastAPI(title="Traveler App API")
app.include_router(gas.router)
app.include_router(maintenance.router)
app.include_router(dashboard.router)
app.include_router(map_router.router)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
