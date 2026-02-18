from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import admin, auth, files, reports
from app.seed import seed_demo_data

app = FastAPI(title="Secure File Sharing Portal", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    settings.upload_path.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        seed_demo_data(db, settings.demo_data_path, settings.upload_path)
    finally:
        db.close()


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "database": settings.database_url,
        "upload_dir": str(settings.upload_path),
    }


app.include_router(auth.router)
app.include_router(files.router)
app.include_router(admin.router)
app.include_router(reports.router)
