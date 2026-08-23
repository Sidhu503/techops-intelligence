"""
TechOps Intelligence Platform - Synthetic Data Generator
=========================================================
Generates:
  - 1000 synthetic IT incidents with postmortems  -> postmortems collection
  - 500  SRE-inspired question-strategy pairs     -> knowledge_base collection
  - 300  synthetic log patterns                   -> logs collection

Usage (from notebook 05 or any pipeline notebook):
----------------------------------------------------
    import sys
    if "generate_synthetic_data" in sys.modules:
        del sys.modules["generate_synthetic_data"]

    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    import generate_synthetic_data as gsd

    gsd.OLLAMA_MODEL     = "qwen2.5:3b-instruct-q4_K_M"
    gsd.BATCH_SIZE       = 10
    gsd.embedding_model  = embedding_model
    gsd.PROJECT_ROOT     = PROJECT_ROOT
    gsd.get_existing_ids = get_existing_ids
    gsd.should_embed     = should_embed
    gsd.embed_and_store  = embed_and_store

    llm = gsd.build_llm()
    gsd.task1_generate_incidents(llm, postmortems_collection,   total=1000)
    gsd.task2_generate_sre_qa(llm,    knowledge_base_collection, total=500)
    gsd.task3_generate_logs(llm,      logs_collection,           total=300)
"""

# ---------------------------------------------------------------------------
# Silence LangSmith telemetry before any langchain import
# ---------------------------------------------------------------------------
import os
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"]    = "false"
os.environ["LANGCHAIN_TRACING"]    = "false"
os.environ["LANGCHAIN_API_KEY"]    = ""
os.environ["LANGSMITH_ENDPOINT"]   = ""

import json
import time
import random
import logging
from pathlib import Path
from typing import Optional

from langchain_ollama import OllamaLLM

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level globals
# Injected by the caller notebook before calling any task function.
# ---------------------------------------------------------------------------
OLLAMA_MODEL    = "qwen2.5:3b-instruct-q4_K_M"
BATCH_SIZE      = 10
TEMPERATURE     = 0.7
PROJECT_ROOT    = None   # injected: Path
embedding_model = None   # injected: SentenceTransformer

# Helper functions injected from the caller notebook
def get_existing_ids(collection) -> set:
    """Placeholder - replaced by caller's implementation at runtime."""
    if collection.count() == 0:
        return set()
    existing = collection.get(include=[])
    return set(existing["ids"])


def should_embed(doc_id: str, existing_ids: set) -> bool:
    """Placeholder - replaced by caller's implementation at runtime."""
    return doc_id not in existing_ids


def embed_and_store(texts, metadatas, ids, collection, model, batch_size=64):
    """
    Placeholder - replaced by caller's implementation at runtime.
    Fallback implementation used only if caller does not inject their own.
    """
    from tqdm import tqdm
    stored = 0
    errors = 0
    for i in tqdm(range(0, len(texts), batch_size),
                  desc=f"Embedding -> {collection.name}"):
        batch_texts = texts[i:i + batch_size]
        batch_meta  = metadatas[i:i + batch_size]
        batch_ids   = ids[i:i + batch_size]

        valid = [
            (t, m, d)
            for t, m, d in zip(batch_texts, batch_meta, batch_ids)
            if t and len(t.strip()) > 10
        ]
        if not valid:
            continue

        v_texts, v_meta, v_ids = zip(*valid)
        try:
            embeddings = model.encode(
                list(v_texts),
                show_progress_bar=False,
                batch_size=batch_size,
            )
            collection.add(
                documents  = list(v_texts),
                embeddings = embeddings.tolist(),
                metadatas  = list(v_meta),
                ids        = list(v_ids),
            )
            stored += len(v_texts)
        except Exception as exc:
            errors += 1
            print(f"  Batch error at {i}: {exc}")

    return stored, errors


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
INCIDENT_CATEGORIES = [
    "database", "memory", "network", "storage",
    "application", "security", "kubernetes", "monitoring",
]
SEVERITIES = ["P1", "P2", "P3", "P4"]

SRE_CATEGORIES = [
    "incident_response", "reliability", "postmortem",
    "capacity_planning", "monitoring", "on_call",
]
SRE_SOURCE_DOCS = ["sre_book", "sre_workbook", "aws_well_architected"]

LOG_CATEGORIES = [
    "database", "memory", "network", "kubernetes",
    "storage", "security", "application",
]
LOG_LEVELS = ["ERROR", "FATAL", "WARN"]


# ---------------------------------------------------------------------------
# Ollama helpers
# ---------------------------------------------------------------------------

def build_llm() -> OllamaLLM:
    """Instantiate the Ollama LLM client."""
    return OllamaLLM(model=OLLAMA_MODEL, temperature=TEMPERATURE)


def call_llm_with_retry(llm: OllamaLLM, prompt: str,
                        retries: int = 1) -> Optional[str]:
    """
    Invoke the LLM with a single retry on failure.
    Returns the response text or None if all attempts fail.
    """
    for attempt in range(retries + 1):
        try:
            return llm.invoke(prompt)
        except Exception as exc:
            if attempt < retries:
                logger.warning(
                    "Ollama call failed (attempt %d/%d): %s -- retrying in 3 s",
                    attempt + 1, retries + 1, exc,
                )
                time.sleep(3)
            else:
                logger.error(
                    "Ollama call failed after %d attempt(s): %s -- skipping batch",
                    retries + 1, exc,
                )
    return None


def safe_json_parse(raw: str, fallback):
    """
    Parse a JSON value from LLM output.
    Strips markdown code fences if present, returns fallback on failure.
    """
    try:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text  = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            ).strip()
        return json.loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.debug("JSON parse failed: %s", exc)
        return fallback


# ---------------------------------------------------------------------------
# Task 1 - Synthetic IT Incidents (1000)
# ---------------------------------------------------------------------------

INCIDENT_PROMPT_TEMPLATE = """\
You are an expert SRE engineer. Generate {count} realistic IT incident postmortems as a JSON array.
Each element must be a JSON object with EXACTLY these fields:
- "incident_id": string like "INC-{start:05d}" incrementing from {start}
- "title": short descriptive incident title (string)
- "category": one of {categories}
- "severity": one of {severities}
- "description": 3-4 sentence detailed description of what happened (string)
- "root_cause": 2-3 sentence root cause analysis (string)
- "resolution_steps": list of 3-5 actionable steps taken to resolve (list of strings)
- "lessons_learned": list of 2-3 lessons learned (list of strings)
- "duration_minutes": integer between 5 and 480

Mix categories and severities realistically. Make descriptions technically accurate for IT operations.
Return ONLY a valid JSON array with {count} objects. No markdown, no explanation."""


def generate_incident_batch(llm: OllamaLLM,
                            batch_start: int,
                            count: int) -> list:
    """Generate a batch of synthetic incidents via Ollama."""
    prompt = INCIDENT_PROMPT_TEMPLATE.format(
        count=count,
        start=batch_start,
        categories=INCIDENT_CATEGORIES,
        severities=SEVERITIES,
    )
    raw = call_llm_with_retry(llm, prompt)
    if raw is None:
        return []

    parsed = safe_json_parse(raw, fallback=[])
    if not isinstance(parsed, list):
        logger.warning("Expected JSON array for incidents, got %s", type(parsed))
        return []

    results = []
    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            continue
        idx = batch_start + i
        results.append({
            "incident_id":       item.get("incident_id",       f"INC-{idx:05d}"),
            "title":             item.get("title",             f"Incident {idx}"),
            "category":          item.get("category",          random.choice(INCIDENT_CATEGORIES)),
            "severity":          item.get("severity",          random.choice(SEVERITIES)),
            "description":       item.get("description",       ""),
            "root_cause":        item.get("root_cause",        ""),
            "resolution_steps":  item.get("resolution_steps",  []),
            "lessons_learned":   item.get("lessons_learned",   []),
            "duration_minutes":  int(item.get("duration_minutes", 60)),
        })
    return results


def task1_generate_incidents(llm: OllamaLLM,
                             postmortems_collection,
                             total: int = 1000) -> None:
    """
    Task 1: Generate synthetic IT incidents, save to JSON, embed into ChromaDB.
    Already-embedded IDs are skipped via should_embed().
    """
    output_path = PROJECT_ROOT / "data" / "processed" / "synthetic_incidents.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ---- Load existing JSON so we skip re-generation ----
    all_incidents: list = []
    if output_path.exists():
        with open(output_path, encoding="utf-8") as fh:
            all_incidents = json.load(fh)
        print(f"Loaded {len(all_incidents)} existing incidents from JSON")

    # ---- Generate only what is missing ----
    already_generated = len(all_incidents)
    remaining         = total - already_generated
    num_batches       = (remaining + BATCH_SIZE - 1) // BATCH_SIZE if remaining > 0 else 0

    if num_batches > 0:
        print(f"Task 1: Generating {remaining} more incidents in {num_batches} batches")
        for batch_num in range(num_batches):
            batch_start = already_generated + batch_num * BATCH_SIZE + 1
            count       = min(BATCH_SIZE, total - len(all_incidents))
            print(f"Processing batch {batch_num + 1} of {num_batches}")

            batch = generate_incident_batch(llm, batch_start, count)
            if not batch:
                logger.warning("Batch %d returned no incidents, skipping", batch_num + 1)
                continue

            all_incidents.extend(batch)
            with open(output_path, "w", encoding="utf-8") as fh:
                json.dump(all_incidents, fh, indent=2)
    else:
        print("Task 1: All incidents already generated, skipping Ollama calls")

    print(f"Total incidents in JSON: {len(all_incidents)}. Path: {output_path}")

    # ---- Embed into ChromaDB (skips already-stored IDs) ----
    print("Embedding incidents into postmortems collection")
    existing_ids = get_existing_ids(postmortems_collection)

    texts, metadatas, ids = [], [], []
    for idx, incident in enumerate(all_incidents):
        doc_id = f"synthetic_incident_{idx}"
        if not should_embed(doc_id, existing_ids):
            continue

        resolution_text = " ".join(incident.get("resolution_steps", []))
        combined_text   = (
            f"{incident['description']} "
            f"{incident['root_cause']} "
            f"{resolution_text}"
        ).strip()

        texts.append(combined_text)
        metadatas.append({
            "source":           "synthetic_incident",
            "category":         incident["category"],
            "severity":         incident["severity"],
            "doc_type":         "postmortem",
            "incident_id":      incident["incident_id"],
            "title":            incident["title"],
            "duration_minutes": incident["duration_minutes"],
        })
        ids.append(doc_id)

    if texts:
        embedded, skipped = embed_and_store(
            texts, metadatas, ids,
            postmortems_collection, embedding_model, BATCH_SIZE,
        )
        print(
            f"Task 1 complete: {embedded} embedded, {skipped} skipped "
            f"out of {len(all_incidents)} total incidents"
        )
    else:
        print("Task 1: All incidents already embedded, nothing new to add")


# ---------------------------------------------------------------------------
# Task 2 - SRE Question-Strategy Pairs (500)
# ---------------------------------------------------------------------------

SRE_QA_PROMPT_TEMPLATE = """\
You are a senior Site Reliability Engineer. Generate {count} realistic SRE question-strategy pairs as a JSON array.
Each element must be a JSON object with EXACTLY these fields:
- "question": a realistic question an on-call engineer would ask during an incident or planning session (string)
- "strategy": detailed SRE-based answer with concrete steps, referencing concepts like error budgets, SLOs, \
toil reduction, blameless postmortems, runbooks, alert fatigue, or capacity planning (2-4 sentences, string)
- "category": one of {categories}
- "source_doc": one of {source_docs}

Draw from real SRE principles: error budgets, SLOs/SLAs/SLIs, blameless postmortems, eliminating toil, \
capacity planning, alert fatigue reduction, runbook automation, on-call rotation health.
Mix categories evenly. Make questions and strategies technically specific.
Return ONLY a valid JSON array with {count} objects. No markdown, no explanation."""


def generate_sre_qa_batch(llm: OllamaLLM, count: int, batch_num: int) -> list:
    """Generate a batch of SRE Q&A pairs via Ollama."""
    prompt = SRE_QA_PROMPT_TEMPLATE.format(
        count=count,
        categories=SRE_CATEGORIES,
        source_docs=SRE_SOURCE_DOCS,
    )
    raw = call_llm_with_retry(llm, prompt)
    if raw is None:
        return []

    parsed = safe_json_parse(raw, fallback=[])
    if not isinstance(parsed, list):
        logger.warning(
            "Expected JSON array for SRE Q&A (batch %d), got %s",
            batch_num, type(parsed),
        )
        return []

    results = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        record = {
            "question":   item.get("question",   ""),
            "strategy":   item.get("strategy",   ""),
            "category":   item.get("category",   random.choice(SRE_CATEGORIES)),
            "source_doc": item.get("source_doc", random.choice(SRE_SOURCE_DOCS)),
        }
        if record["question"] and record["strategy"]:
            results.append(record)
    return results


def task2_generate_sre_qa(llm: OllamaLLM,
                          knowledge_base,
                          total: int = 500) -> None:
    """
    Task 2: Generate SRE Q&A pairs, save to JSON, embed into knowledge_base collection.
    Already-embedded IDs are skipped via should_embed().
    """
    output_path = PROJECT_ROOT / "data" / "processed" / "sre_qa_pairs.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ---- Load existing JSON ----
    all_pairs: list = []
    if output_path.exists():
        with open(output_path, encoding="utf-8") as fh:
            all_pairs = json.load(fh)
        print(f"Loaded {len(all_pairs)} existing SRE Q&A pairs from JSON")

    # ---- Generate only what is missing ----
    already_generated = len(all_pairs)
    remaining         = total - already_generated
    num_batches       = (remaining + BATCH_SIZE - 1) // BATCH_SIZE if remaining > 0 else 0

    if num_batches > 0:
        print(f"Task 2: Generating {remaining} more SRE Q&A pairs in {num_batches} batches")
        for batch_num in range(num_batches):
            count = min(BATCH_SIZE, total - len(all_pairs))
            print(f"Processing batch {batch_num + 1} of {num_batches}")

            batch = generate_sre_qa_batch(llm, count, batch_num + 1)
            if not batch:
                logger.warning("Batch %d returned no Q&A pairs, skipping", batch_num + 1)
                continue

            all_pairs.extend(batch)
            with open(output_path, "w", encoding="utf-8") as fh:
                json.dump(all_pairs, fh, indent=2)
    else:
        print("Task 2: All SRE Q&A pairs already generated, skipping Ollama calls")

    print(f"Total SRE Q&A pairs in JSON: {len(all_pairs)}. Path: {output_path}")

    # ---- Embed into ChromaDB ----
    print("Embedding SRE Q&A pairs into knowledge_base collection")
    existing_ids = get_existing_ids(knowledge_base)

    texts, metadatas, ids = [], [], []
    for idx, pair in enumerate(all_pairs):
        doc_id = f"sre_qa_{idx}"
        if not should_embed(doc_id, existing_ids):
            continue

        combined_text = f"{pair['question']} {pair['strategy']}".strip()
        texts.append(combined_text)
        metadatas.append({
            "source":     "sre_qa",
            "category":   pair["category"],
            "source_doc": pair["source_doc"],
            "doc_type":   "sre_knowledge",
        })
        ids.append(doc_id)

    if texts:
        embedded, skipped = embed_and_store(
            texts, metadatas, ids,
            knowledge_base, embedding_model, BATCH_SIZE,
        )
        print(
            f"Task 2 complete: {embedded} embedded, {skipped} skipped "
            f"out of {len(all_pairs)} total Q&A pairs"
        )
    else:
        print("Task 2: All SRE Q&A pairs already embedded, nothing new to add")


# ---------------------------------------------------------------------------
# Task 3 - Synthetic Log Patterns (300)
# ---------------------------------------------------------------------------

LOG_PROMPT_TEMPLATE = """\
You are a Linux systems and Kubernetes expert. Generate {count} realistic server log lines as a JSON array.
Each element must be a JSON object with EXACTLY these fields:
- "log_line": a single realistic log line including timestamp, log level, service name, and message (string)
  Format example: "2024-01-15 03:42:17 ERROR [postgres-primary] Connection pool exhausted: max_connections=100 reached"
- "severity": one of {levels}
- "category": one of {categories}

Rules:
- Use ISO timestamps like "2024-MM-DD HH:MM:SS"
- Log levels must be {levels} only
- Include realistic service names (e.g., postgres-replica, kube-apiserver, nginx-ingress, redis-cache, etcd)
- Include realistic technical details: memory addresses, port numbers, connection counts, latency values
- Each log line must be self-contained and actionable for an on-call engineer
- Distribute categories evenly
Return ONLY a valid JSON array with {count} objects. No markdown, no explanation."""


def generate_log_batch(llm: OllamaLLM, count: int, batch_num: int) -> list:
    """Generate a batch of synthetic log lines via Ollama."""
    prompt = LOG_PROMPT_TEMPLATE.format(
        count=count,
        levels=LOG_LEVELS,
        categories=LOG_CATEGORIES,
    )
    raw = call_llm_with_retry(llm, prompt)
    if raw is None:
        return []

    parsed = safe_json_parse(raw, fallback=[])
    if not isinstance(parsed, list):
        logger.warning(
            "Expected JSON array for logs (batch %d), got %s",
            batch_num, type(parsed),
        )
        return []

    results = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        log_line = item.get("log_line", "").strip()
        if not log_line:
            continue
        results.append({
            "log_line": log_line,
            "severity": item.get("severity", random.choice(LOG_LEVELS)),
            "category": item.get("category", random.choice(LOG_CATEGORIES)),
        })
    return results


def task3_generate_logs(llm: OllamaLLM,
                        logs_collection,
                        total: int = 300) -> None:
    """
    Task 3: Generate synthetic log patterns, save backup JSON, embed into logs collection.
    Already-embedded IDs are skipped via should_embed().
    """
    output_path = PROJECT_ROOT / "data" / "processed" / "synthetic_logs.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ---- Load existing JSON ----
    all_logs: list = []
    if output_path.exists():
        with open(output_path, encoding="utf-8") as fh:
            all_logs = json.load(fh)
        print(f"Loaded {len(all_logs)} existing log patterns from JSON")

    # ---- Generate only what is missing ----
    already_generated = len(all_logs)
    remaining         = total - already_generated
    num_batches       = (remaining + BATCH_SIZE - 1) // BATCH_SIZE if remaining > 0 else 0

    if num_batches > 0:
        print(f"Task 3: Generating {remaining} more log patterns in {num_batches} batches")
        for batch_num in range(num_batches):
            count = min(BATCH_SIZE, total - len(all_logs))
            print(f"Processing batch {batch_num + 1} of {num_batches}")

            batch = generate_log_batch(llm, count, batch_num + 1)
            if not batch:
                logger.warning("Batch %d returned no log lines, skipping", batch_num + 1)
                continue

            all_logs.extend(batch)
            with open(output_path, "w", encoding="utf-8") as fh:
                json.dump(all_logs, fh, indent=2)
    else:
        print("Task 3: All log patterns already generated, skipping Ollama calls")

    print(f"Total log patterns in JSON: {len(all_logs)}. Backup: {output_path}")

    # ---- Embed into ChromaDB ----
    print("Embedding log patterns into logs collection")
    existing_ids = get_existing_ids(logs_collection)

    texts, metadatas, ids = [], [], []
    for idx, log in enumerate(all_logs):
        doc_id = f"synthetic_log_{idx}"
        if not should_embed(doc_id, existing_ids):
            continue

        texts.append(log["log_line"])
        metadatas.append({
            "source":   "synthetic_it_ops_logs",
            "severity": log["severity"],
            "doc_type": "log_pattern",
            "category": log["category"],
        })
        ids.append(doc_id)

    if texts:
        embedded, skipped = embed_and_store(
            texts, metadatas, ids,
            logs_collection, embedding_model, BATCH_SIZE,
        )
        print(
            f"Task 3 complete: {embedded} embedded, {skipped} skipped "
            f"out of {len(all_logs)} total log patterns"
        )
    else:
        print("Task 3: All log patterns already embedded, nothing new to add")


# ---------------------------------------------------------------------------
# Direct execution guard
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    raise RuntimeError(
        "This module must be imported, not run directly. "
        "See the module docstring for usage instructions."
    )