from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.upload import router as upload_router
from routes.live_audio import router as live_audio_router

app = FastAPI(
    title="OverWatch API",
    description="Backend service for OverWatch real-time audio pipeline simulation dashboard",
    version="0.3.0"
)

# Configure CORS for frontend access during local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(upload_router, prefix="/api")
app.include_router(live_audio_router, prefix="/api")


@app.get("/")
def root():
    return {
        "service": "OverWatch API",
        "phase": 2,
        "status": "online"
    }
