"""
TechOps Intelligence Platform — FastAPI Backend
FinTechFlow incident intelligence API

Endpoints:
    POST /analyse  → run full 4-agent pipeline
    GET  /health   → system health status
    GET  /metrics  → usage statistics
"""
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Optional, List
from collections import defaultdict

os.environ["LANGCHAIN_TRACING_V2"]          = "false"
os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = "false"
os.environ["LANGCHAIN_API_KEY"]              = ""
os.environ["ANONYMIZED_TELEMETRY"]           = "False"
os.environ["TOKENIZERS_PARALLELISM"]         = "false"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.agents.pipeline import run_incident


# ── App Setup ─────────────────────────────────────────────
app = FastAPI(
    title       = "TechOps Intelligence API",
    description = "FinTechFlow incident intelligence powered by LangGraph",
    version     = "1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"]
)


# ── Request / Response Models ──────────────────────────────
class IncidentRequest(BaseModel):
    incident_text: str = Field(
        ...,
        min_length  = 10,
        max_length  = 5000,
        description = "Raw incident description or alert text"
    )
    source: str = Field(
        default     = "api",
        description = "Source of the incident (api/streamlit/pagerduty)"
    )


class IncidentResponse(BaseModel):
    incident_id          : str
    severity             : str
    category             : str
    severity_confidence  : float
    category_confidence  : float
    severity_source      : str
    root_cause           : str
    diagnosis_confidence : float
    resolution_steps     : List[str]
    estimated_time_mins  : int
    escalation_needed    : bool
    stakeholder_message  : str
    postmortem_draft     : str
    agent_latencies      : dict
    total_latency_s      : float
    retrieved_incidents  : List[str]
    retrieved_postmortems: List[str]
    retrieved_runbooks   : List[str]
    error                : Optional[str]


class HealthResponse(BaseModel):
    status     : str
    version    : str
    pipeline   : str
    llm_model  : str
    collections: dict


class MetricsResponse(BaseModel):
    total_incidents   : int
    avg_latency_s     : float
    severity_breakdown: dict
    category_breakdown: dict


# ── In-memory metrics store ────────────────────────────────
_metrics = {
    "total"         : 0,
    "latencies"     : [],
    "severities"    : defaultdict(int),
    "categories"    : defaultdict(int)
}


# ── Endpoints ─────────────────────────────────────────────
@app.post("/analyse", response_model=IncidentResponse)
async def analyse_incident(request: IncidentRequest):
    """
    Run full 4-agent pipeline on incident text.
    Returns severity, root cause, resolution steps,
    stakeholder message and postmortem draft.
    """
    if not request.incident_text.strip():
        raise HTTPException(
            status_code = 400,
            detail      = "incident_text cannot be empty"
        )

    incident_id = f"FTF-{str(uuid.uuid4())[:8].upper()}"

    try:
        result = run_incident(request.incident_text)

        # Update metrics
        total_lat = result["agent_latencies"].get("total", 0)
        _metrics["total"]                              += 1
        _metrics["latencies"].append(total_lat)
        _metrics["severities"][result["severity"]]    += 1
        _metrics["categories"][result["category"]]    += 1

        return IncidentResponse(
            incident_id          = incident_id,
            severity             = result.get("severity", "P2"),
            category             = result.get("category", "application"),
            severity_confidence  = result.get("severity_confidence", 0.0),
            category_confidence  = result.get("category_confidence", 0.0),
            severity_source      = result.get("severity_source", "distilbert"),
            root_cause           = result.get("root_cause", ""),
            diagnosis_confidence = result.get("diagnosis_confidence", 0.0),
            resolution_steps     = result.get("resolution_steps", []),
            estimated_time_mins  = result.get("estimated_time_mins", 30),
            escalation_needed    = result.get("escalation_needed", False),
            stakeholder_message  = result.get("stakeholder_message", ""),
            postmortem_draft     = result.get("postmortem_draft", ""),
            agent_latencies      = result.get("agent_latencies", {}),
            total_latency_s      = result.get("agent_latencies", {}).get("total", 0.0),
            retrieved_incidents  = result.get("retrieved_incidents", []),
            retrieved_postmortems= result.get("retrieved_postmortems", []),
            retrieved_runbooks   = result.get("retrieved_runbooks", []),
            error                = result.get("error")
)

    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail      = f"Pipeline error: {str(e)}"
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check."""
    try:
        import chromadb
        from pathlib import Path
        client = chromadb.PersistentClient(
            path=str(Path(__file__).resolve().parents[1]
                     / "data/embeddings/chroma_db")
        )
        collections = {
            col.name: client.get_collection(col.name).count()
            for col in client.list_collections()
        }
    except Exception:
        collections = {}

    return HealthResponse(
        status      = "healthy",
        version     = "1.0.0",
        pipeline    = "triage → diagnosis → resolution → comms",
        llm_model   = "qwen2.5:7b",
        collections = collections
    )


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Pipeline usage statistics."""
    total    = _metrics["total"]
    lats     = _metrics["latencies"]
    avg_lat  = round(sum(lats) / len(lats), 2) if lats else 0.0

    return MetricsResponse(
        total_incidents    = total,
        avg_latency_s      = avg_lat,
        severity_breakdown = dict(_metrics["severities"]),
        category_breakdown = dict(_metrics["categories"])
    )


@app.get("/")
async def root():
    return {
        "name"       : "TechOps Intelligence API",
        "company"    : "FinTechFlow",
        "version"    : "1.0.0",
        "docs"       : "/docs",
        "endpoints"  : ["/analyse", "/health", "/metrics"]
    }
