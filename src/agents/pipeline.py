"""
TechOps Intelligence Platform — Agent Pipeline
FinTechFlow incident intelligence system

Usage:
    from src.agents.pipeline import run_incident

    result = run_incident(
        "PostgreSQL connection refused port 5432"
    )
"""
import os
import sys
import time
from pathlib import Path
from typing import TypedDict, Optional, List

os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, END

from src.agents.triage_classifier import classify_incident
from src.retrieval.retriever import retrieve


class AgentState(TypedDict):
    incident_text        : str
    severity             : str
    category             : str
    severity_confidence  : float
    category_confidence  : float
    severity_source      : str
    retrieved_incidents  : List[str]
    retrieved_postmortems: List[str]
    root_cause           : str
    diagnosis_confidence : float
    retrieved_runbooks   : List[str]
    resolution_steps     : List[str]
    estimated_time_mins  : int
    escalation_needed    : bool
    stakeholder_message  : str
    postmortem_draft     : str
    agent_latencies      : dict
    error                : Optional[str]


_llm = None
def get_llm(temperature=0.1):
    return Ollama(
        model       = "qwen2.5:7b-instruct-q4_K_M",
        base_url    = "http://localhost:11434",
        temperature = temperature,
        num_ctx     = 4096
    )


def triage_node(state):
    start  = time.time()
    result = classify_incident(state["incident_text"])
    state.update({
        "severity"           : result["severity"],
        "category"           : result["category"],
        "severity_confidence": result["severity_confidence"],
        "category_confidence": result["category_confidence"],
        "severity_source"    : result.get("severity_source", "distilbert"),
    })
    state["agent_latencies"]["triage"] = round(time.time()-start, 3)
    return state


DIAGNOSIS_PROMPT = PromptTemplate.from_template("""
You are a senior SRE at FinTechFlow.
INCIDENT: {incident_text}
SEVERITY: {severity} | CATEGORY: {category}
CONTEXT: {context}
ROOT_CAUSE: [one sentence]
CONFIDENCE: [HIGH/MEDIUM/LOW]
IMMEDIATE_ACTION: [first step]
""")


def diagnosis_node(state):
    start    = time.time()
    llm      = get_llm(0.1)
    incidents = retrieve(state["incident_text"],
                         ["incidents"], top_k_return=3)
    pms       = retrieve(state["incident_text"],
                         ["postmortems"], top_k_return=3)
    context   = "\n".join([r["text"][:300]
                            for r in incidents + pms])
    response  = llm.invoke(DIAGNOSIS_PROMPT.format(
        incident_text=state["incident_text"],
        severity=state["severity"],
        category=state["category"],
        context=context[:1500]
    ))
    root_cause = "Root cause under investigation"
    for line in response.split("\n"):
        if line.startswith("ROOT_CAUSE:"):
            root_cause = line.replace("ROOT_CAUSE:", "").strip()
    state.update({
        "root_cause"           : root_cause,
        "diagnosis_confidence" : 0.8,
        "retrieved_incidents"  : [r["text"][:200] for r in incidents],
        "retrieved_postmortems": [r["text"][:200] for r in pms],
    })
    state["agent_latencies"]["diagnosis"] = round(time.time()-start, 3)
    return state


RESOLUTION_PROMPT = PromptTemplate.from_template("""
Senior SRE at FinTechFlow. Create resolution plan.
INCIDENT: {incident_text}
ROOT CAUSE: {root_cause}
RUNBOOKS: {runbooks}
STEPS:
1. [action]
2. [action]
3. [action]
4. [verify]
ESTIMATED_TIME: [X minutes]
""")


def resolution_node(state):
    start    = time.time()
    llm      = get_llm(0.1)
    runbooks = retrieve(
        f"{state['category']} {state['incident_text'][:150]}",
        ["knowledge_base", "playbooks"], top_k_return=3
    )
    rb_text  = "\n".join([r["text"][:300] for r in runbooks])
    response = llm.invoke(RESOLUTION_PROMPT.format(
        incident_text=state["incident_text"][:200],
        root_cause=state["root_cause"],
        runbooks=rb_text[:1000]
    ))
    steps    = []
    est_time = 30
    in_steps = False
    for line in response.split("\n"):
        line = line.strip()
        if line == "STEPS:":
            in_steps = True
        elif line.startswith("ESTIMATED_TIME:"):
            in_steps = False
            try:
                est_time = int("".join(filter(str.isdigit, line)))
            except Exception:
                est_time = 30
        elif in_steps and line and line[0].isdigit():
            steps.append(line)
    state.update({
        "resolution_steps"   : steps or ["Check logs", "Restart service", "Verify"],
        "estimated_time_mins": est_time,
        "escalation_needed"  : state["severity"] == "P1",
        "retrieved_runbooks" : [r["text"][:200] for r in runbooks],
    })
    state["agent_latencies"]["resolution"] = round(time.time()-start, 3)
    return state


COMMS_PROMPT = PromptTemplate.from_template("""
Incident commander at FinTechFlow.
INCIDENT: {incident_text}
SEVERITY: {severity} | ROOT CAUSE: {root_cause}
ETA: {eta} minutes
SLACK_MESSAGE:
[3-4 sentence update for #incidents channel]
POSTMORTEM_OUTLINE:
Title: [title]
Summary: [summary]
""")


def comms_node(state):
    start    = time.time()
    llm      = get_llm(0.4)
    response = llm.invoke(COMMS_PROMPT.format(
        incident_text=state["incident_text"][:200],
        severity=state["severity"],
        root_cause=state["root_cause"],
        eta=state.get("estimated_time_mins", 30)
    ))
    slack = ""
    pm    = ""
    in_s  = False
    in_p  = False
    for line in response.split("\n"):
        if "SLACK_MESSAGE:" in line:
            in_s = True; in_p = False; continue
        if "POSTMORTEM_OUTLINE:" in line:
            in_s = False; in_p = True; continue
        if in_s and line.strip():
            slack += line + "\n"
        if in_p and line.strip():
            pm += line + "\n"
    state.update({
        "stakeholder_message": slack.strip() or f"[{state['severity']}] Incident in progress.",
        "postmortem_draft"   : pm.strip() or f"Title: {state['category']} incident\nSeverity: {state['severity']}",
    })
    state["agent_latencies"]["comms"] = round(time.time()-start, 3)
    return state


def build_pipeline():
    g = StateGraph(AgentState)
    g.add_node("triage",     triage_node)
    g.add_node("diagnosis",  diagnosis_node)
    g.add_node("resolution", resolution_node)
    g.add_node("comms",      comms_node)
    g.set_entry_point("triage")
    g.add_edge("triage",     "diagnosis")
    g.add_edge("diagnosis",  "resolution")
    g.add_edge("resolution", "comms")
    g.add_edge("comms",      END)
    return g.compile()


_pipeline = None

def run_incident(incident_text: str) -> dict:
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()

    state = AgentState(
        incident_text        = incident_text,
        severity             = "",
        category             = "",
        severity_confidence  = 0.0,
        category_confidence  = 0.0,
        severity_source      = "",
        retrieved_incidents  = [],
        retrieved_postmortems= [],
        root_cause           = "",
        diagnosis_confidence = 0.0,
        retrieved_runbooks   = [],
        resolution_steps     = [],
        estimated_time_mins  = 0,
        escalation_needed    = False,
        stakeholder_message  = "",
        postmortem_draft     = "",
        agent_latencies      = {},
        error                = None
    )
    start              = time.time()
    result             = _pipeline.invoke(state)
    result["agent_latencies"]["total"] = round(time.time()-start, 3)
    return result
