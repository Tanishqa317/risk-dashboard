from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.flatline import router as flatline_router
from app.routes.correlation import router as correlation_router
from app.routes.cost_translator import router as cost_translator_router
from app.routes.guardrail import router as guardrail_router
from app.routes.permit_detector import router as permit_detector_router
from app.routes.replay import router as replay_router
from app.routes.evidence_chain import router as evidence_chain_router
from app.routes.evac_routing import router as evac_routing_router
from app.routes.vibration_check import router as vibration_check_router

app = FastAPI(title="risk-dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api"

app.include_router(flatline_router, prefix=api_prefix)
app.include_router(correlation_router, prefix=api_prefix)
app.include_router(cost_translator_router, prefix=api_prefix)
app.include_router(guardrail_router, prefix=api_prefix)
app.include_router(permit_detector_router, prefix=api_prefix)
app.include_router(replay_router, prefix=api_prefix)
app.include_router(evidence_chain_router, prefix=api_prefix)
app.include_router(evac_routing_router, prefix=api_prefix)
app.include_router(vibration_check_router, prefix=api_prefix)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "risk-dashboard backend is running"}
