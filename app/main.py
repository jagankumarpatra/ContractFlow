from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title="ContractFlow API",
    description="Contract Lifecycle Management API — B2B SaaS platform for managing contracts with AI-powered analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "service": "contractflow",
        "version": "1.0.0"
    }

@app.get("/", tags=["Health"])
def root():
    return {"message": "ContractFlow API — visit /docs for documentation"}
