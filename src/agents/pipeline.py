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
def get_llm(temperature=0.1, max_tokens=300):
    return Ollama(
        model       = "qwen2.5:7b",
        base_url    = "http://localhost:11434",
        temperature = temperature,
        num_ctx     = 1024,
        num_predict = max_tokens 
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
Reply in exactly this format:
ROOT_CAUSE: [two to three sentences summary of root cause]
CONFIDENCE: [HIGH/MEDIUM/LOW]
IMMEDIATE_ACTION: [first step]
""")


from concurrent.futures import ThreadPoolExecutor

def diagnosis_node(state):
    start = time.time()
    llm   = get_llm(0.1, max_tokens=200)

    print(f"[DIAGNOSIS] Retrieving in parallel...")

    # Run both retrievals simultaneously
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_inc = executor.submit(
            retrieve,
            state["incident_text"],
            ["incidents"],
            10,    # top_k_fetch
            3,     # top_k_return
            0.4,   # bm25_weight
            0.6,   # semantic_weight
            True,  # use_reranking
            None   # filter_metadata
        )
        future_pm = executor.submit(
            retrieve,
            state["incident_text"],
            ["postmortems"],
            10,
            3,
            0.4,
            0.6,
            True,
            None
        )
        incidents = future_inc.result()
        pms       = future_pm.result()

    print(f"[DIAGNOSIS] Retrieved {len(incidents)} incidents, "
          f"{len(pms)} postmortems")

    context = "\n".join([
        r["text"][:150] for r in incidents + pms
    ])

    print(f"[DIAGNOSIS] Generating diagnosis with LLM...")

    response = llm.invoke(DIAGNOSIS_PROMPT.format(
        incident_text = state["incident_text"],
        severity      = state["severity"],
        category      = state["category"],
        context       = context[:1000]
    ))

    root_cause = "Root cause under investigation"
    for line in response.split("\n"):
        if line.strip().startswith("ROOT_CAUSE:"):
            root_cause = line.replace("ROOT_CAUSE:", "").strip()
            break

    state["root_cause"]            = root_cause
    state["diagnosis_confidence"]  = 0.8
    state["retrieved_incidents"]   = [r["text"] for r in incidents]
    state["retrieved_postmortems"] = [r["text"] for r in pms]
    state["agent_latencies"]["diagnosis"] = round(
        time.time() - start, 3
    )
    return state


RESOLUTION_PROMPT = PromptTemplate.from_template("""
Senior SRE at FinTechFlow. Create resolution plan.Be concise.
INCIDENT: {incident_text}
ROOT CAUSE: {root_cause}
RUNBOOKS: {runbooks}
Reply in exactly this format:
STEPS:
1. [action]
2. [action]
3. [action]
4. [verify]
ESTIMATED_TIME: [X minutes]
""")


def resolution_node(state):
    start = time.time()
    llm   = get_llm(0.1, max_tokens=200)

    print(f"[RESOLUTION] Retrieving runbooks in parallel...")

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_kb = executor.submit(
            retrieve,
            f"{state['category']} {state['incident_text'][:150]}",
            ["knowledge_base"],
            10, 3, 0.4, 0.6, True, None
        )
        future_pb = executor.submit(
            retrieve,
            f"{state['category']} {state['incident_text'][:150]}",
            ["playbooks"],
            10, 3, 0.4, 0.6, True, None
        )
        kb_results = future_kb.result()
        pb_results = future_pb.result()

    runbooks  = kb_results + pb_results
    rb_text   = "\n".join([r["text"][:150] for r in runbooks])

    print(f"[RESOLUTION] Retrieved {len(runbooks)} entries")
    print(f"[RESOLUTION] Generating resolution plan...")

    response  = llm.invoke(RESOLUTION_PROMPT.format(
        incident_text = state["incident_text"][:200],
        root_cause    = state["root_cause"],
        runbooks      = rb_text[:1000]
    ))

    steps    = []
    est_time = 30
    in_steps = False

    for line in response.split("\n"):
        line = line.strip()
        if line == "STEPS:":
            in_steps = True
            continue
        if line.startswith("ESTIMATED_TIME:"):
            in_steps = False
            try:
                est_time = int("".join(filter(str.isdigit, line)))
            except Exception:
                est_time = 30
        elif in_steps and line and line[0].isdigit():
            steps.append(line)

    state["resolution_steps"]    = steps or [
        "Check service logs",
        "Restart affected service",
        "Verify recovery"
    ]
    state["estimated_time_mins"] = est_time
    state["escalation_needed"]   = state["severity"] == "P1"
    state["retrieved_runbooks"]  = [r["text"] for r in runbooks]
    state["agent_latencies"]["resolution"] = round(
        time.time() - start, 3
    )
    return state


COMMS_PROMPT = PromptTemplate.from_template("""
You are an incident commander at FinTechFlow.
IMPORTANT: Respond in English only.

INCIDENT: {incident_text}
SEVERITY: {severity}
ROOT CAUSE: {root_cause}
ETA: {eta} minutes

Write ONLY the following two sections, nothing else:

SLACK_MESSAGE:
[Write 2-3 sentences in English for #incidents Slack channel. Include severity, what failed, and ETA.]

POSTMORTEM_OUTLINE:
Title: [English title]
Summary: [One to two English sentence summary]
Root Cause: {root_cause}
Status: Investigating
ETA: {eta} minutes
""")



def comms_node(state):
    start = time.time()
    llm   = get_llm(0.4, max_tokens=135)

    response = llm.invoke(COMMS_PROMPT.format(
        incident_text = state["incident_text"][:200],
        severity      = state["severity"],
        root_cause    = state["root_cause"],
        eta           = state.get("estimated_time_mins", 30)
    ))

    print(f"[COMMS RAW]:\n{response}\n")

    slack = ""
    pm    = ""
    in_s  = False
    in_p  = False

    for line in response.split("\n"):
        stripped = line.strip()

        if stripped.startswith("SLACK_MESSAGE:"):
            in_s   = True
            in_p   = False
            inline = stripped.replace("SLACK_MESSAGE:", "").strip()
            if inline:
                slack += inline + "\n"
            continue

        if stripped.startswith("POSTMORTEM_OUTLINE:"):
            in_s = False
            in_p = True
            continue

        if in_s and stripped and not stripped.startswith("POSTMORTEM"):
            slack += stripped + "\n"

        if in_p and stripped:
            pm += stripped + "\n"

    # Clean prefix artifacts
    slack = slack.strip()
    if slack.startswith("_MESSAGE:"):
        slack = slack.replace("_MESSAGE:", "").strip()

    # Fallback if parsing failed
    if not slack:
        slack = (
            f"[{state['severity']}] FinTechFlow incident: "
            f"{state['category']} issue detected. "
            f"Root cause: {state['root_cause'][:120]}. "
            f"ETA: {state.get('estimated_time_mins', 30)} mins. "
            f"Team investigating — updates every 5 mins."
        )

    if not pm:
        pm = (
            f"Title: {state['category'].title()} Incident\n"
            f"Severity: {state['severity']}\n"
            f"Root Cause: {state['root_cause']}\n"
            f"Status: Investigating\n"
            f"ETA: {state.get('estimated_time_mins', 30)} mins"
        )

    state["stakeholder_message"]      = slack.strip()
    state["postmortem_draft"]         = pm.strip()
    state["agent_latencies"]["comms"] = round(time.time() - start, 3)
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
