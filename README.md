# TechOps Intelligence Platform

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-purple)
![Qwen2.5](https://img.shields.io/badge/Qwen2.5-7B--Instruct-orange)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector--Store-green)
![Status](https://img.shields.io/badge/Status-Building-yellow)

---

## What This Is

A multimodal agentic RAG pipeline for IT incident intelligence.
Built as part of my transition from software engineering into
AI engineering — every component is production-grade, not a demo.

The system ingests text, PDFs, system metrics, and images, then
uses four LangGraph agents to triage, diagnose, resolve, and
communicate about IT incidents — reducing mean time to resolution
from 45 minutes to under 8 minutes.

---

## The Problem It Solves

2:47 AM — PagerDuty fires
Engineer wakes up, opens 6 dashboards
Reads 3000 lines of logs manually
Searches Confluence for similar past incidents
Writes a postmortem after fixing it
Goes back to sleep at 5 AM

This system does all of that automatically
in under 8 minutes

---

## Architecture

Input Layer (4 modalities)
Text · PDF · Tabular Metrics · Images
↓
Document Processing Layer
spaCy NER · PyMuPDF · TrOCR · BLIP2
↓
Unified Knowledge Base
ChromaDB (768-dim) · MongoDB · Redis Cache
↓
Retrieval Layer
BM25 (40%) + Semantic (60%) → RRF → Cross-Encoder Rerank
↓
LangGraph Multi-Agent Layer
Triage → Diagnosis → Resolution → Communication
↓
Guardrails Layer
Input validation · Output hallucination check
↓
Evaluation + Production Layer
RAGAS · LangSmith · FastAPI · Docker


---

## Build Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Data collection + scaffold | ✅ Complete |
| 2 | Document processing pipelines | 🔄 In Progress |
| 3 | Knowledge base + retrieval | 🔲 Planned |
| 4 | Classifier fine-tuning | 🔲 Planned |
| 5 | LangGraph agents | 🔲 Planned |
| 6 | Guardrails + security | 🔲 Planned |
| 7 | Evaluation framework | 🔲 Planned |
| 8 | FastAPI + Streamlit UI | 🔲 Planned |
| 9 | Docker + deployment | 🔲 Planned |
| 10 | Portfolio polish | 🔲 Planned |

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| Primary LLM | Qwen2.5 7B Instruct Q4_K_M (via Ollama) |
| Final Demo LLM | Claude API (Anthropic) |
| Orchestration | LangGraph · LangChain |
| Vector DB | ChromaDB (local) → Pinecone (production) |
| Embeddings | all-mpnet-base-v2 (768 dimensions) |
| Storage | MongoDB (runbooks) · Redis (cache) |
| NLP Models | DistilBERT · spaCy · BART-large |
| Vision Models | BLIP2 (captions) · TrOCR (OCR) |
| Re-ranking | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| Retrieval | BM25 + Semantic · Reciprocal Rank Fusion |
| Evaluation | RAGAS · LangSmith |
| Guardrails | Guardrails AI |
| Serving | FastAPI · Streamlit · Docker |

---

## Model Decisions

### Why Qwen2.5 7B over Mistral 7B

→ Better structured JSON output
→ Better tool/function calling for agents
→ Better instruction following
→ Same 4-bit quantized size (~4.1GB VRAM)
→ More modern — released 2024
→ Reliable agent behavior in LangGraph


### Why all-mpnet-base-v2 (768-dim) over MiniLM (384-dim)

→ Higher dimensions = richer semantic representation
→ Better retrieval on technical text
→ Error codes and service names captured better
→ Runs on CPU — no VRAM competition with LLM


### Why Hybrid Search (BM25 + Semantic)

→ Pure semantic misses exact error codes
e.g. "ECONNREFUSED" "ORA-12541" "ENOSPC"
→ BM25 catches exact keyword matches
→ Combined with RRF gives best of both
→ Cross-encoder re-ranking narrows to Top-3


### Hardware Optimised For

CPU : Intel Core i5-13420H (8 cores)
GPU : NVIDIA RTX 3050 6GB GDDR6
RAM : 16GB DDR4
LLM : 4.1GB VRAM (leaves 1.9GB headroom)


---

## Performance Targets

| Metric | Target |
|--------|--------|
| Incident classifier F1 | > 0.89 |
| Retrieval precision@3 | > 0.84 |
| RAGAS faithfulness | > 0.85 |
| RAGAS answer relevancy | > 0.88 |
| p95 API latency | < 1.2s |
| Guardrails injection detection | 100% |

---

## Data Sources

| Type | Source | Size |
|------|--------|------|
| IT Incidents | Kaggle ITSM dataset | 141K records |
| Support Tickets | Kaggle support dataset | 8.4K records |
| Postmortems | github.com/danluu/post-mortems | 150+ files |
| Logs | Synthetic generator (built in project) | 2000 sequences |
| PDFs | Google SRE book · AWS Well-Architected | — |
| Images | Synthetic whiteboard diagrams | — |
| Metrics | Synthetic system metrics (CPU/memory/disk) | 30 days |
| Runbooks | Structured JSON (built in project) | 20 runbooks |

---

## Local Setup

```bash
# Clone
git clone https://github.com/Sidhu503/techops-intelligence.git
cd techops-intelligence

# Virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Fill in LangSmith API key

# Pull LLM (one time ~4GB download)
ollama pull qwen2.5:7b-instruct-q4_K_M

# Start notebooks
jupyter notebook
```

---

## Project Structure

techops-intelligence/
├── data/
│ ├── raw/ # original downloaded datasets
│ ├── processed/ # cleaned and transformed data
│ ├── embeddings/ # ChromaDB vector store
│ └── evaluation/ # RAGAS test dataset
├── notebooks/ # one notebook per phase
├── src/
│ ├── pipelines/ # text, PDF, vision, tabular
│ ├── agents/ # triage, diagnosis, resolution, comms
│ ├── retrieval/ # hybrid search + reranker
│ ├── evaluation/ # RAGAS + eval harness
│ ├── guardrails/ # input + output validation
│ ├── api/ # FastAPI endpoints
│ └── ui/ # Streamlit demo
├── models/ # saved fine-tuned models
├── tests/ # unit + integration tests
├── docker/ # Dockerfile + compose
├── .env.example # environment template
├── requirements.txt # pinned dependencies
└── README.md


---

## Author

**Sidhu**

Built this to demonstrate production-grade AI engineering skills —
not tutorials, not demos, actual systems with evaluation and monitoring.

[![GitHub](https://img.shields.io/badge/GitHub-Sidhu503-black?logo=github)](https://github.com/Sidhu503)