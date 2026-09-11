"""
Generate 100 FinTechFlow runbooks
Run: python src/data_generation/generate_runbooks.py
"""
import json
import time
import re
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED    = PROJECT_ROOT / "data/processed"
OUTPUT       = PROCESSED / "ftf_runbooks.json"
CHECKPOINT   = PROCESSED / "ftf_runbooks_checkpoint.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "qwen2.5:7b"

RUNBOOK_TOPICS = [
    # DATABASE — 20 runbooks
    ("PostgreSQL max_connections exhausted", "database", "payments-sre", "P1"),
    ("PostgreSQL disk full on WAL directory", "database", "payments-sre", "P1"),
    ("PostgreSQL replication lag exceeded threshold", "database", "payments-sre", "P2"),
    ("PostgreSQL deadlock storm on transactions table", "database", "payments-sre", "P2"),
    ("PgBouncer connection pooler unresponsive", "database", "payments-sre", "P1"),
    ("PostgreSQL autovacuum bloat degrading query performance", "database", "payments-sre", "P2"),
    ("PostgreSQL backup job failing silently", "database", "payments-sre", "P2"),
    ("PostgreSQL slow queries causing timeout cascade", "database", "payments-sre", "P2"),
    ("PostgreSQL streaming replication slot bloat", "database", "payments-sre", "P1"),
    ("PostgreSQL sequence overflow risk", "database", "payments-sre", "P1"),
    ("Redis maxmemory eviction storm", "database", "platform-sre", "P2"),
    ("Redis cluster node failure and failover", "database", "platform-sre", "P2"),
    ("Redis sentinel failover not completing", "database", "platform-sre", "P2"),
    ("Redis cache stampede after flush", "database", "platform-sre", "P1"),
    ("Redis AOF rewrite causing disk I/O saturation", "database", "platform-sre", "P2"),
    ("Elasticsearch heap exhaustion", "database", "platform-sre", "P1"),
    ("Elasticsearch circuit breaker triggered", "database", "platform-sre", "P2"),
    ("Elasticsearch shard allocation failed", "database", "platform-sre", "P2"),
    ("Elasticsearch index corruption recovery", "database", "platform-sre", "P2"),
    ("Elasticsearch cluster split-brain recovery", "database", "platform-sre", "P1"),
    # NETWORK — 20 runbooks
    ("AWS ALB all targets unhealthy", "network", "platform-sre", "P1"),
    ("Route53 DNS resolution failure", "network", "platform-sre", "P1"),
    ("Kafka consumer group lag critical", "network", "platform-sre", "P1"),
    ("Kafka broker disk full", "network", "platform-sre", "P1"),
    ("Kafka partition leadership rebalance", "network", "platform-sre", "P2"),
    ("Cloudflare SSL certificate expired", "network", "security-sre", "P1"),
    ("Cloudflare false positive blocking payments", "network", "security-sre", "P1"),
    ("AWS NAT Gateway port exhaustion", "network", "platform-sre", "P2"),
    ("AWS Security Group blocking service traffic", "network", "platform-sre", "P1"),
    ("VPC peering route missing", "network", "platform-sre", "P1"),
    ("Kafka producer timeout and backpressure", "network", "platform-sre", "P2"),
    ("Kafka offset commit failure", "network", "platform-sre", "P2"),
    ("Route53 health check failure causing failover", "network", "platform-sre", "P2"),
    ("AWS ALB target group draining stuck", "network", "platform-sre", "P2"),
    ("Cloudflare rate limiting misconfiguration", "network", "security-sre", "P2"),
    ("AWS Transit Gateway route failure", "network", "platform-sre", "P1"),
    ("Kafka exactly-once semantics violation", "network", "platform-sre", "P1"),
    ("ALB access log delivery failure", "network", "platform-sre", "P3"),
    ("Kafka topic deletion orphaned partitions", "network", "platform-sre", "P3"),
    ("Route53 weighted routing misconfiguration", "network", "platform-sre", "P1"),
    # MEMORY — 10 runbooks
    ("JVM OOMKilled pod memory limit exceeded", "memory", "payments-sre", "P1"),
    ("Java GC overhead limit exceeded", "memory", "payments-sre", "P1"),
    ("Python worker OOM killed by OS", "memory", "payments-sre", "P2"),
    ("JVM metaspace exhaustion", "memory", "payments-sre", "P2"),
    ("Redis maxmemory eviction causing session loss", "memory", "platform-sre", "P2"),
    ("Kafka Streams state store OOMKilled", "memory", "platform-sre", "P2"),
    ("Elasticsearch field data cache exhaustion", "memory", "platform-sre", "P2"),
    ("Java thread stack overflow", "memory", "payments-sre", "P2"),
    ("Node.js heap exhaustion", "memory", "payments-sre", "P2"),
    ("Go goroutine leak causing memory growth", "memory", "payments-sre", "P2"),
    # STORAGE — 10 runbooks
    ("EBS volume ENOSPC on PostgreSQL data directory", "storage", "payments-sre", "P1"),
    ("Kafka log partition filling data disk", "storage", "platform-sre", "P1"),
    ("S3 throttling blocking transaction log pipeline", "storage", "data-sre", "P2"),
    ("EBS volume stuck in detaching state", "storage", "platform-sre", "P2"),
    ("EBS IOPS limit hit causing I/O wait", "storage", "payments-sre", "P2"),
    ("S3 lifecycle policy deleted active data", "storage", "data-sre", "P1"),
    ("Elasticsearch translog corruption recovery", "storage", "platform-sre", "P2"),
    ("PostgreSQL pg_wal filling faster than archiving", "storage", "payments-sre", "P1"),
    ("EBS multi-attach filesystem corruption", "storage", "platform-sre", "P1"),
    ("Kafka log compaction deleting unprocessed messages", "storage", "platform-sre", "P2"),
    # APPLICATION — 15 runbooks
    ("Payment service circuit breaker opened", "application", "payments-sre", "P1"),
    ("Fraud detection service timeout cascade", "application", "payments-sre", "P1"),
    ("Transaction processor duplicate payment detection", "application", "payments-sre", "P1"),
    ("Order service CrashLoopBackOff after deployment", "application", "platform-sre", "P2"),
    ("Notification service Kafka consumer lag backlog", "application", "payments-sre", "P2"),
    ("Merchant API rate limiter misconfiguration", "application", "payments-sre", "P1"),
    ("Payment service graceful shutdown during deployment", "application", "payments-sre", "P2"),
    ("Fraud detection ML model stale data rollback", "application", "payments-sre", "P2"),
    ("Transaction processor idempotency violation", "application", "payments-sre", "P1"),
    ("Payment service thread pool exhaustion", "application", "payments-sre", "P1"),
    ("Order service database migration failure recovery", "application", "payments-sre", "P1"),
    ("Notification service dead letter queue overflow", "application", "payments-sre", "P2"),
    ("Payment service health check false eviction", "application", "platform-sre", "P2"),
    ("Merchant API pagination causing incomplete exports", "application", "payments-sre", "P3"),
    ("Feature flag rollout causing scoring regression", "application", "payments-sre", "P2"),
    # SECURITY — 10 runbooks
    ("HashiCorp Vault sealed emergency procedure", "security", "security-sre", "P1"),
    ("AWS WAF false positive blocking payments", "security", "security-sre", "P1"),
    ("SSL certificate expired emergency renewal", "security", "security-sre", "P1"),
    ("AWS IAM AccessDenied blocking service operations", "security", "security-sre", "P2"),
    ("API key rotation failure recovery", "security", "security-sre", "P2"),
    ("Vault token TTL causing secret refresh storm", "security", "security-sre", "P2"),
    ("mTLS certificate rotation procedure", "security", "security-sre", "P2"),
    ("AWS KMS key policy blocking encryption", "security", "security-sre", "P1"),
    ("Cloudflare firewall blocking legitimate traffic", "security", "security-sre", "P1"),
    ("AWS Secrets Manager rotation failure", "security", "security-sre", "P2"),
    # KUBERNETES — 10 runbooks
    ("EKS node NotReady recovery procedure", "kubernetes", "platform-sre", "P1"),
    ("Pod CrashLoopBackOff investigation and fix", "kubernetes", "platform-sre", "P2"),
    ("ArgoCD sync failure recovery", "kubernetes", "platform-sre", "P2"),
    ("etcd high latency risk mitigation", "kubernetes", "platform-sre", "P1"),
    ("Ingress controller 502 all pods unhealthy", "kubernetes", "platform-sre", "P1"),
    ("EKS cluster autoscaler failure during surge", "kubernetes", "platform-sre", "P1"),
    ("Kubernetes HPA misconfiguration rollback", "kubernetes", "platform-sre", "P2"),
    ("PodDisruptionBudget emergency override", "kubernetes", "platform-sre", "P1"),
    ("EKS control plane API server degradation", "kubernetes", "platform-sre", "P2"),
    ("Kubernetes network policy blocking service traffic", "kubernetes", "platform-sre", "P1"),
    # MONITORING — 5 runbooks
    ("PagerDuty alert storm response procedure", "monitoring", "platform-sre", "P1"),
    ("Prometheus scrape target down investigation", "monitoring", "platform-sre", "P2"),
    ("Grafana no data during active incident", "monitoring", "platform-sre", "P2"),
    ("Alert Manager route misconfiguration fix", "monitoring", "platform-sre", "P1"),
    ("Prometheus TSDB corruption recovery", "monitoring", "platform-sre", "P2"),
]


def build_runbook_prompt(topic: str, category: str,
                          team: str, severity: str,
                          idx: int) -> str:
    return f"""You are a senior SRE at FinTechFlow writing a runbook.

FinTechFlow: B2B payment processor, 50M transactions/day.
Stack: Java Spring Boot, PostgreSQL (port 5432), Redis (port 6379),
Kafka (port 9092), Kubernetes EKS, Vault, Prometheus, Grafana, PagerDuty.
Services: payment-service, order-service, transaction-processor,
fraud-detection-service, notification-service, merchant-api.
Team: {team}

Write a runbook for: {topic}
Runbook ID: FTF-RB-{idx:02d}
Typical severity: {severity}

Return ONLY this JSON object:
{{
  "runbook_id": "FTF-RB-{idx:02d}",
  "title": "{topic}",
  "category": "{category}",
  "team": "{team}",
  "severity_when_triggered": "{severity}",
  "symptoms": [
    "specific symptom 1 as seen in Prometheus or PagerDuty",
    "specific symptom 2 with metric name or log pattern",
    "specific symptom 3 user facing impact"
  ],
  "diagnosis_steps": [
    "step 1: exact kubectl, psql, redis-cli or AWS CLI command to run",
    "step 2: what output to look for and what it means",
    "step 3: decision point - what determines next action"
  ],
  "resolution_steps": [
    "step 1: exact remediation command with explanation",
    "step 2: follow-up action",
    "step 3: verification command and expected healthy output"
  ],
  "escalation": "when to escalate: specific threshold and who to page at FinTechFlow",
  "rollback": "exact rollback procedure if fix makes situation worse",
  "prevention": "specific technical improvement to prevent recurrence",
  "related_alerts": [
    "PromQL alert name or Grafana dashboard name 1",
    "alert name 2"
  ]
}}"""


def call_ollama(prompt: str) -> str:
    payload = {
        "model"  : MODEL,
        "prompt" : prompt,
        "stream" : False,
        "options": {
            "temperature": 0.5,
            "num_predict": 1200,
            "top_p"      : 0.9
        }
    }
    for attempt in range(3):
        try:
            r = requests.post(
                OLLAMA_URL, json=payload, timeout=150
            )
            if r.status_code == 200:
                return r.json().get("response", "")
        except Exception as e:
            print(f"  Attempt {attempt+1}: {e}")
            time.sleep(2)
    return ""


def extract_json(text: str) -> dict:
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text).strip()
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else {}
    except Exception:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return {}


def load_checkpoint() -> list:
    if CHECKPOINT.exists():
        with open(CHECKPOINT) as f:
            data = json.load(f)
        print(f"Checkpoint: {len(data)} runbooks done")
        return data
    return []


def main():
    print("FinTechFlow Runbook Generator")
    print(f"Target: {len(RUNBOOK_TOPICS)} runbooks")

    runbooks     = load_checkpoint()
    already_done = len(runbooks)
    to_run       = RUNBOOK_TOPICS[already_done:]

    for i, (topic, category, team, severity) in \
            enumerate(to_run, already_done + 1):

        if i % 20 == 1:
            print(f"Progress: {i}/{len(RUNBOOK_TOPICS)} - {topic[:40]}")

        prompt   = build_runbook_prompt(
            topic, category, team, severity, i
        )
        response = call_ollama(prompt)
        parsed   = extract_json(response)

        if not parsed:
            parsed = {
                "runbook_id"              : f"FTF-RB-{i:02d}",
                "title"                   : topic,
                "category"                : category,
                "team"                    : team,
                "severity_when_triggered" : severity,
                "symptoms"                : ["Alert fired in PagerDuty"],
                "diagnosis_steps"         : ["Check Grafana dashboard"],
                "resolution_steps"        : ["Follow standard procedure"],
                "escalation"              : f"Escalate to {team} lead after 15 mins",
                "prevention"              : "Add monitoring threshold"
            }

        runbooks.append(parsed)

        if len(runbooks) % 25 == 0:
            with open(CHECKPOINT, 'w') as f:
                json.dump(runbooks, f, indent=2)
            print(f"Checkpoint: {len(runbooks)} runbooks saved")

        time.sleep(0.5)

    with open(OUTPUT, 'w') as f:
        json.dump(runbooks, f, indent=2)

    if CHECKPOINT.exists():
        CHECKPOINT.unlink()

    print(f"\nSaved {len(runbooks)} runbooks")


if __name__ == "__main__":
    main()