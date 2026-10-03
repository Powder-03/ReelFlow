from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router

app = FastAPI(
    title="Multi-Agent Instagram Growth Brain",
    description="Autonomous Multi-Agent Content Intelligence, Strategy, Hinglish Script Generation, and Calibrated G-Eval Evaluation.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "Multi-Agent Instagram Growth Brain is running",
        "docs_url": "/docs",
        "health_check": "/api/health",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
