"""
TechOps Intelligence Platform — Streamlit Demo UI
FinTechFlow incident intelligence demo

Run: streamlit run src/ui/app.py
"""
import os
import sys
import time
import requests
from pathlib import Path

os.environ["LANGCHAIN_TRACING_V2"]          = "false"
os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = "false"
os.environ["LANGCHAIN_API_KEY"]              = ""
os.environ["ANONYMIZED_TELEMETRY"]           = "False"
os.environ["TOKENIZERS_PARALLELISM"]         = "false"

import streamlit as st

# ── Page Config ───────────────────────────────────────────
st.set_page_config(
    page_title = "TechOps Intelligence — FinTechFlow",
    page_icon  = "🔧",
    layout     = "wide"
)

API_URL = "http://localhost:8000"

# ── Header ────────────────────────────────────────────────
st.title("TechOps Intelligence Platform")
st.caption("FinTechFlow B2B Payment Processor — Incident Intelligence System")
st.divider()

# ── Sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.header("About")
    st.markdown("""
    **Multimodal Agentic RAG Pipeline**

    4-agent LangGraph system for IT incident intelligence:
    - Triage Agent — severity + category
    - Diagnosis Agent — root cause via RAG
    - Resolution Agent — runbook steps
    - Comms Agent — stakeholder message

    **Stack**
    - LLM: Qwen2.5 7B (Ollama)
    - Vector DB: ChromaDB
    - Classifier: DistilBERT
    - Retrieval: BM25 + Semantic + Reranking
    """)

    st.divider()
    st.header("Demo Scenarios")

    demo_scenarios = {
        "Database P1 — PostgreSQL": "ALERT: payment-service pods failing health checks. PostgreSQL connection refused on port 5432. Error: ECONNREFUSED max_connections=200 reached. 50,000 transactions pending. Team: payments-sre",
        "Security P1 — Vault Sealed": "CRITICAL: HashiCorp Vault sealed unexpectedly during AWS KMS key rotation. All microservices unable to read secrets. payment-service, order-service, fraud-detection all failing. Team: security-sre",
        "Kubernetes P1 — CrashLoop": "ERROR: payment-service pod CrashLoopBackOff restarts=24 OOMKilled memory limit 4Gi exceeded. 15 pods evicted from EKS cluster. Transactions queuing. Team: platform-sre",
        "Network P2 — Kafka Lag": "WARNING: Kafka consumer group lag reached 2.4M messages on topic=payment-events. transaction-processor falling behind. ETA to backlog clear unknown. Team: platform-sre",
        "Monitoring P2 — Alert Storm": "WARNING: PagerDuty alert storm. 400 alerts in 5 minutes from payment-service. Alert Manager misconfigured. Real P1 incidents may be masked. Team: platform-sre"
    }

    selected = st.selectbox(
        "Load demo scenario:",
        ["-- Select --"] + list(demo_scenarios.keys())
    )

    if selected != "-- Select --":
        st.session_state["demo_text"] = demo_scenarios[selected]

    st.divider()

    # System health
    st.header("System Status")
    try:
        health = requests.get(f"{API_URL}/health", timeout=10).json()
        st.success(f"API: {health['status']}")
        st.caption(f"LLM: {health['llm_model']}")
        for name, count in health.get("collections", {}).items():
            st.caption(f"{name}: {count:,} docs")
    except Exception:
        st.error("API offline — start FastAPI server")

# ── Main Input ────────────────────────────────────────────
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Incident Input")
    incident_text = st.text_area(
        "Paste incident alert or describe the issue:",
        value       = st.session_state.get("demo_text", ""),
        height      = 150,
        placeholder = "e.g. PostgreSQL connection refused on port 5432..."
    )

with col2:
    st.subheader("Quick Info")
    st.info("""
    **What this system does:**

    1. Classifies severity (P1/P2/P3)
    2. Identifies root cause
    3. Retrieves fix steps from runbooks
    4. Drafts stakeholder message
    """)

analyse_btn = st.button(
    "Analyse Incident",
    type = "primary",
    use_container_width = True
)

# ── Pipeline Execution ────────────────────────────────────
if analyse_btn and incident_text.strip():
    st.divider()
    st.subheader("Agent Pipeline Execution")

    # Show agent progress
    progress_cols = st.columns(4)
    agent_names   = ["Triage", "Diagnosis", "Resolution", "Comms"]
    agent_status  = {}

    for i, name in enumerate(agent_names):
        with progress_cols[i]:
            agent_status[name] = st.empty()
            agent_status[name].info(f"**{name}**\nWaiting...")

    # Call API
    with st.spinner("Running incident through agent pipeline..."):
        start = time.time()

        # Update statuses progressively
        agent_status["Triage"].warning("**Triage**\nRunning...")

        try:
            response = requests.post(
                f"{API_URL}/analyse",
                json    = {"incident_text": incident_text, "source": "streamlit"},
                timeout = 300
            )

            if response.status_code == 200:
                result = response.json()
                total  = time.time() - start

                # Update agent statuses with latencies
                lats = result.get("agent_latencies", {})
                agent_status["Triage"].success(
                    f"**Triage**\n"
                    f"Done ({lats.get('triage', 0):.2f}s)"
                )
                agent_status["Diagnosis"].success(
                    f"**Diagnosis**\n"
                    f"Done ({lats.get('diagnosis', 0):.2f}s)"
                )
                agent_status["Resolution"].success(
                    f"**Resolution**\n"
                    f"Done ({lats.get('resolution', 0):.2f}s)"
                )
                agent_status["Comms"].success(
                    f"**Comms**\n"
                    f"Done ({lats.get('comms', 0):.2f}s)"
                )

                st.divider()

                # ── Results ──────────────────────────────
                st.subheader("Results")

                # Severity badge + Category
                r1, r2, r3, r4 = st.columns(4)

                severity    = result["severity"]
                sev_colors  = {
                    "P1": "🔴", "P2": "🟠",
                    "P3": "🟡", "P4": "🟢"
                }
                sev_icon = sev_colors.get(severity, "⚪")

                with r1:
                    st.metric(
                        "Severity",
                        f"{sev_icon} {severity}",
                        f"conf: {result['severity_confidence']:.0%}"
                    )
                with r2:
                    st.metric(
                        "Category",
                        result["category"].title(),
                        f"conf: {result['category_confidence']:.0%}"
                    )
                with r3:
                    st.metric(
                        "ETA",
                        f"{result['estimated_time_mins']} mins",
                        "to resolution"
                    )
                with r4:
                    st.metric(
                        "Total Latency",
                        f"{result['total_latency_s']:.1f}s",
                        "pipeline runtime"
                    )

                st.divider()

                # Root cause
                st.subheader("Root Cause")
                st.error(result["root_cause"])

                # Resolution steps
                st.subheader("Resolution Steps")
                steps = result["resolution_steps"]
                if steps:
                    for i, step in enumerate(steps, 1):
                        st.write(f"**{i}.** {step}")
                else:
                    st.write("No steps generated")

                # Two columns for message and postmortem
                mc1, mc2 = st.columns(2)

                with mc1:
                    st.subheader("Stakeholder Slack Message")
                    msg = result.get("stakeholder_message", "")
                    if msg:
                        st.info(msg)
                    else:
                        st.warning("No message generated")
                    st.caption(f"Severity source: {result.get('severity_source', 'unknown')}")

                with mc2:
                    st.subheader("Postmortem Draft")
                    st.text_area(
                        "Postmortem outline:",
                        value  = result["postmortem_draft"],
                        height = 200
                    )

                # Retrieved sources
                with st.expander("Retrieved Sources"):
                    st.write("**Similar Incidents:**")
                    incidents = result.get("retrieved_incidents", [])
                    if incidents:
                        for i, inc in enumerate(incidents[:3], 1):
                            st.markdown(f"**{i}.** {inc}")
                            st.divider()
                    else:
                        st.caption("No similar incidents found")

                    st.write("**Relevant Postmortems:**")
                    postmortems = result.get("retrieved_postmortems", [])
                    if postmortems:
                        for i, pm in enumerate(postmortems[:3], 1):
                            st.markdown(f"**{i}.** {pm}")
                            st.divider()
                    else:
                        st.caption("No postmortems found")

                    st.write("**Runbook Entries Used:**")
                    runbooks = result.get("retrieved_runbooks", [])
                    if runbooks:
                        for i, rb in enumerate(runbooks[:3], 1):
                            st.markdown(f"**{i}.** {rb}")
                            st.divider()
                    else:
                        st.caption("No runbooks found")

                # Latency breakdown
                with st.expander("Agent Latency Breakdown"):
                    for agent, lat in lats.items():
                        bar_len = int(lat / 60 * 20)
                        bar     = "█" * bar_len + "░" * (20 - bar_len)
                        st.code(f"{agent:12} [{bar}] {lat:.2f}s")

                # Incident ID
                st.caption(
                    f"Incident ID: {result['incident_id']} | "
                    f"Source: {result.get('severity_source', 'unknown')}"
                )

            else:
                st.error(f"API error {response.status_code}: {response.text}")

        except requests.exceptions.Timeout:
            st.error("Request timed out — pipeline is running, please wait and retry")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to API — ensure FastAPI server is running")
        except Exception as e:
            st.error(f"Error: {str(e)}")

elif analyse_btn and not incident_text.strip():
    st.warning("Please enter an incident description")

# ── Footer ────────────────────────────────────────────────
st.divider()
st.caption(
    "TechOps Intelligence Platform v1.0 | "
    "FinTechFlow SRE | "
    "Built with LangGraph + ChromaDB + DistilBERT"
)
