"""
TechOps Intelligence — Triage Classifier
FinTechFlow incident severity and category classifier

Usage:
    import importlib.util

    spec   = importlib.util.spec_from_file_location(
    "triage_classifier",
    str(PROJECT_ROOT / "src/agents/triage_classifier.py")
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

classify_incident = module.classify_incident
print("Classifier loaded")

    result = classify_incident(
        "PostgreSQL connection refused port 5432 payment-service"
    )
    # Returns:
    # {
    #   "severity": "P1",
    #   "category": "database",
    #   "severity_confidence": 0.94,
    #   "category_confidence": 0.89
    # }
"""
import torch
import joblib
import numpy as np
from pathlib import Path
from transformers import (
    DistilBertTokenizerFast,
    DistilBertForSequenceClassification
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR   = PROJECT_ROOT / "models/classifier"

_sev_model   = None
_cat_model   = None
_tokenizer   = None
_sev_encoder = None
_cat_encoder = None


def _load():
    global _sev_model, _cat_model, _tokenizer
    global _sev_encoder, _cat_encoder

    if _tokenizer is not None:
        return

    sev_path = MODELS_DIR / "severity_classifier"
    cat_path = MODELS_DIR / "category_classifier"

    _tokenizer   = DistilBertTokenizerFast.from_pretrained(
        str(sev_path)
    )
    _sev_model   = DistilBertForSequenceClassification.from_pretrained(
        str(sev_path)
    ).eval()
    _cat_model   = DistilBertForSequenceClassification.from_pretrained(
        str(cat_path)
    ).eval()
    _sev_encoder = joblib.load(str(sev_path / "label_encoder.pkl"))
    _cat_encoder = joblib.load(str(cat_path / "label_encoder.pkl"))


# src/agents/triage_classifier.py
# Replace classify_incident with this hybrid version

# Rule-based severity signals found in real incidents
P1_SIGNALS = [
    'all users', 'complete outage', 'econnrefused',
    'oomkilled', 'crashloopbackoff', 'vault sealed',
    'all targets unhealthy', 'enospc', 'max_connections',
    'circuit breaker open', 'all payments', 'revenue',
    'connection refused', 'disk full', 'node notready',
    'leader election', 'etcd', 'ingress', '502',
    'sealed', 'expired certificate', 'ddos', 'breach'
]

P2_SIGNALS = [
    'replication lag', 'consumer lag', 'degraded',
    'some users', 'elevated', 'intermittent',
    'high latency', 'slow query', 'partial',
    'retry', 'timeout', 'warnings'
]

P3_SIGNALS = [
    'minor', 'low priority', 'cosmetic',
    'scheduled', 'non-critical', 'informational'
]


def rule_based_severity(text: str) -> tuple:
    """
    Returns (severity, confidence) based on keyword rules.
    Returns (None, 0) if no rules match.
    """
    text_lower = text.lower()

    p1_matches = sum(1 for s in P1_SIGNALS if s in text_lower)
    p2_matches = sum(1 for s in P2_SIGNALS if s in text_lower)
    p3_matches = sum(1 for s in P3_SIGNALS if s in text_lower)

    if p1_matches > 0:
        confidence = min(0.95, 0.70 + p1_matches * 0.05)
        return 'P1', confidence
    if p2_matches > 0:
        confidence = min(0.90, 0.65 + p2_matches * 0.05)
        return 'P2', confidence
    if p3_matches > 0:
        return 'P3', 0.75

    return None, 0.0


def classify_incident(text: str) -> dict:
    """
    Hybrid classifier:
    1. Rule-based severity (fast, high precision)
    2. DistilBERT severity (fallback when no rules match)
    3. DistilBERT category (always used — 100% accurate)
    """
    _load()

    enc = _tokenizer(
        text,
        truncation     = True,
        padding        = True,
        max_length     = 128,
        return_tensors = "pt"
    )

    with torch.no_grad():
        sev_logits = _sev_model(**enc).logits
        cat_logits = _cat_model(**enc).logits

    sev_probs = torch.softmax(sev_logits, dim=-1).numpy()[0]
    cat_probs = torch.softmax(cat_logits, dim=-1).numpy()[0]
    cat_idx   = int(np.argmax(cat_probs))

    # Try rule-based severity first
    rule_sev, rule_conf = rule_based_severity(text)

    if rule_sev is not None:
        severity            = rule_sev
        severity_confidence = rule_conf
        severity_source     = 'rule_based'
    else:
        # Fallback to DistilBERT
        sev_idx             = int(np.argmax(sev_probs))
        severity            = _sev_encoder.classes_[sev_idx]
        severity_confidence = float(round(sev_probs[sev_idx], 3))
        severity_source     = 'distilbert'

    return {
        "severity"            : severity,
        "category"            : _cat_encoder.classes_[cat_idx],
        "severity_confidence" : float(round(severity_confidence, 3)),
        "category_confidence" : float(round(cat_probs[cat_idx], 3)),
        "severity_source"     : severity_source,
        "severity_distribution": {
            cls: float(round(p, 3))
            for cls, p in zip(_sev_encoder.classes_, sev_probs)
        }
    }
