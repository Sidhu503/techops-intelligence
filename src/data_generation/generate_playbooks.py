"""
Generate 100 FinTechFlow incident response playbooks
Run: python src/data_generation/generate_playbooks.py
"""
import json
import time
import re
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED    = PROJECT_ROOT / "data/processed"
OUTPUT       = PROCESSED / "ftf_playbooks.json"
CHECKPOINT   = PROCESSED / "ftf_playbooks_checkpoint.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "qwen2.5:7b"

PLAYBOOK_TOPICS = [
    # DATABASE — 20
    ("PostgreSQL complete outage response", "database", "P1", "payments-sre"),
    ("PostgreSQL high connection count response", "database", "P1", "payments-sre"),
    ("PostgreSQL disk full emergency response", "database", "P1", "payments-sre"),
    ("PostgreSQL replication lag response", "database", "P2", "payments-sre"),
    ("PostgreSQL deadlock resolution", "database", "P2", "payments-sre"),
    ("PgBouncer failure response", "database", "P1", "payments-sre"),
    ("Redis cache failure response", "database", "P2", "platform-sre"),
    ("Redis memory exhaustion response", "database", "P2", "platform-sre"),
    ("Redis cluster node failure response", "database", "P2", "platform-sre"),
    ("Elasticsearch outage response", "database", "P1", "platform-sre"),
    ("Elasticsearch high memory response", "database", "P2", "platform-sre"),
    ("Elasticsearch red cluster recovery", "database", "P2", "platform-sre"),
    ("PostgreSQL backup failure response", "database", "P2", "payments-sre"),
    ("PostgreSQL slow query storm response", "database", "P2", "payments-sre"),
    ("Redis eviction storm response", "database", "P2", "platform-sre"),
    ("PostgreSQL autovacuum bloat response", "database", "P2", "payments-sre"),
    ("Elasticsearch shard failure response", "database", "P2", "platform-sre"),
    ("PostgreSQL sequence overflow response", "database", "P1", "payments-sre"),
    ("Redis split-brain response", "database", "P1", "platform-sre"),
    ("Database connection pool exhaustion", "database", "P1", "payments-sre"),
    # NETWORK — 20
    ("AWS ALB complete failure response", "network", "P1", "platform-sre"),
    ("Route53 DNS outage response", "network", "P1", "platform-sre"),
    ("Kafka broker failure response", "network", "P1", "platform-sre"),
    ("Kafka consumer lag critical response", "network", "P1", "platform-sre"),
    ("Cloudflare outage response", "network", "P1", "security-sre"),
    ("VPC connectivity loss response", "network", "P1", "platform-sre"),
    ("AWS NAT Gateway failure response", "network", "P1", "platform-sre"),
    ("Kafka partition leader failure", "network", "P2", "platform-sre"),
    ("Cloudflare false positive response", "network", "P2", "security-sre"),
    ("Route53 failover triggered response", "network", "P2", "platform-sre"),
    ("Kafka topic corruption response", "network", "P1", "platform-sre"),
    ("ALB target group health check failure", "network", "P2", "platform-sre"),
    ("AWS Security Group lockout response", "network", "P1", "platform-sre"),
    ("Cloudflare DDoS attack response", "network", "P1", "security-sre"),
    ("Kafka duplicate message response", "network", "P1", "payments-sre"),
    ("Route53 wrong region failover", "network", "P2", "platform-sre"),
    ("AWS Transit Gateway failure response", "network", "P1", "platform-sre"),
    ("Kafka consumer group rebalance storm", "network", "P2", "platform-sre"),
    ("Cloudflare certificate renewal response", "network", "P2", "security-sre"),
    ("AWS ALB stickiness session loss response", "network", "P2", "platform-sre"),
    # MEMORY — 10
    ("Payment service OOMKilled response", "memory", "P1", "payments-sre"),
    ("Java GC overhead limit response", "memory", "P1", "payments-sre"),
    ("JVM memory leak response", "memory", "P2", "payments-sre"),
    ("Python worker OOM response", "memory", "P2", "payments-sre"),
    ("Node.js heap exhaustion response", "memory", "P2", "payments-sre"),
    ("Redis maxmemory response", "memory", "P2", "platform-sre"),
    ("Kafka Streams OOMKilled response", "memory", "P2", "platform-sre"),
    ("Elasticsearch memory exhaustion response", "memory", "P2", "platform-sre"),
    ("Java metaspace exhaustion response", "memory", "P2", "payments-sre"),
    ("Container memory limit breach response", "memory", "P2", "platform-sre"),
    # STORAGE — 10
    ("EBS volume full emergency response", "storage", "P1", "payments-sre"),
    ("Kafka disk full response", "storage", "P1", "platform-sre"),
    ("S3 access failure response", "storage", "P2", "data-sre"),
    ("EBS volume detach stuck response", "storage", "P2", "platform-sre"),
    ("PostgreSQL WAL disk full response", "storage", "P1", "payments-sre"),
    ("S3 lifecycle delete active data response", "storage", "P1", "data-sre"),
    ("Elasticsearch translog corruption response", "storage", "P2", "platform-sre"),
    ("EBS IOPS exhaustion response", "storage", "P2", "payments-sre"),
    ("Kafka log corruption response", "storage", "P1", "platform-sre"),
    ("EBS filesystem corruption response", "storage", "P1", "platform-sre"),
    # APPLICATION — 15
    ("Payment service complete outage response", "application", "P1", "payments-sre"),
    ("Circuit breaker open response", "application", "P1", "payments-sre"),
    ("Duplicate payment detection response", "application", "P1", "payments-sre"),
    ("Fraud detection outage response", "application", "P1", "payments-sre"),
    ("Transaction processor failure response", "application", "P1", "payments-sre"),
    ("Bad deployment rollback procedure", "application", "P2", "platform-sre"),
    ("Payment service high error rate response", "application", "P2", "payments-sre"),
    ("Notification service backlog response", "application", "P2", "payments-sre"),
    ("Merchant API rate limiting incident", "application", "P2", "payments-sre"),
    ("Fraud model false positive surge response", "application", "P2", "payments-sre"),
    ("Payment service thread pool exhaustion", "application", "P1", "payments-sre"),
    ("Database migration failure recovery", "application", "P1", "payments-sre"),
    ("Feature flag rollout regression response", "application", "P2", "payments-sre"),
    ("Dead letter queue overflow response", "application", "P2", "payments-sre"),
    ("Order service crash loop response", "application", "P2", "platform-sre"),
    # SECURITY — 10
    ("HashiCorp Vault seal emergency response", "security", "P1", "security-sre"),
    ("SSL certificate expired emergency response", "security", "P1", "security-sre"),
    ("AWS WAF blocking payments response", "security", "P1", "security-sre"),
    ("Security breach response procedure", "security", "P1", "security-sre"),
    ("mTLS failure response", "security", "P1", "security-sre"),
    ("API key compromise response", "security", "P1", "security-sre"),
    ("AWS IAM lockout response", "security", "P2", "security-sre"),
    ("Vault token expiry storm response", "security", "P2", "security-sre"),
    ("AWS KMS key issue response", "security", "P1", "security-sre"),
    ("Cloudflare firewall blocking response", "security", "P1", "security-sre"),
    # KUBERNETES — 10
    ("EKS cluster outage response", "kubernetes", "P1", "platform-sre"),
    ("Payment service pod failure response", "kubernetes", "P1", "payments-sre"),
    ("EKS node failure response", "kubernetes", "P1", "platform-sre"),
    ("ArgoCD deployment failure response", "kubernetes", "P2", "platform-sre"),
    ("Ingress controller failure response", "kubernetes", "P1", "platform-sre"),
    ("etcd degradation response", "kubernetes", "P1", "platform-sre"),
    ("HPA runaway scaling response", "kubernetes", "P2", "platform-sre"),
    ("EKS autoscaler failure response", "kubernetes", "P1", "platform-sre"),
    ("Network policy lockout response", "kubernetes", "P1", "platform-sre"),
    ("Pod eviction storm response", "kubernetes", "P2", "platform-sre"),
    # MONITORING — 5
    ("Alert storm response procedure", "monitoring", "P1", "platform-sre"),
    ("Monitoring stack outage response", "monitoring", "P1", "platform-sre"),
    ("Prometheus scrape failure response", "monitoring", "P2", "platform-sre"),
    ("Alert Manager failure response", "monitoring", "P1", "platform-sre"),
    ("PagerDuty escalation failure response", "monitoring", "P1", "platform-sre"),
]


def build_playbook_prompt(topic: str, category: str,
                           severity: str, team: str,
                           idx: int) -> str:
    return f"""You are a senior SRE at FinTechFlow writing an incident response playbook.

FinTechFlow: B2B payment processor, 50M transactions/day.
Stack: Java Spring Boot, PostgreSQL, Redis, Kafka, EKS, Vault, Prometheus, Grafana.
Services: payment-service, order-service, transaction-processor,
fraud-detection-service, notification-service, merchant-api.
Team: {team}

Write a response playbook for: {topic}
Playbook ID: FTF-PB-{idx:03d}
Severity: {severity}

Return ONLY this JSON object:
{{
  "playbook_id": "FTF-PB-{idx:03d}",
  "title": "{topic}",
  "category": "{category}",
  "severity": "{severity}",
  "team": "{team}",
  "trigger": "specific PagerDuty alert or Grafana threshold that triggers this playbook",
  "triage_steps": [
    "T+0: immediate action to assess scope",
    "T+5: second assessment step",
    "T+10: decision point with exact criteria"
  ],
  "response_phases": [
    {{
      "phase": "Detect",
      "duration": "0-5 minutes",
      "actions": ["action 1 with tool and command", "action 2"]
    }},
    {{
      "phase": "Contain",
      "duration": "5-15 minutes",
      "actions": ["containment action 1", "containment action 2"]
    }},
    {{
      "phase": "Resolve",
      "duration": "15-30 minutes",
      "actions": ["resolution action 1 with exact command", "action 2"]
    }},
    {{
      "phase": "Verify",
      "duration": "30-45 minutes",
      "actions": ["verification step 1", "confirmation metric to check"]
    }}
  ],
  "communication_template": "short template message to send to merchants/stakeholders",
  "escalation_criteria": "specific condition requiring escalation beyond {team}",
  "rollback_procedure": "exact steps to rollback if response makes situation worse",
  "related_runbook": "FTF-RB-XX",
  "post_incident": "immediate action required after resolution before closing incident"
}}"""


def call_ollama(prompt: str) -> str:
    payload = {
        "model"  : MODEL,
        "prompt" : prompt,
        "stream" : False,
        "options": {
            "temperature": 0.6,
            "num_predict": 1400,
            "top_p"      : 0.9
        }
    }
    for attempt in range(3):
        try:
            r = requests.post(
                OLLAMA_URL, json=payload, timeout=180
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
        print(f"Checkpoint: {len(data)} playbooks done")
        return data
    return []


def main():
    print("FinTechFlow Playbook Generator")
    print(f"Target: {len(PLAYBOOK_TOPICS)} playbooks")

    playbooks    = load_checkpoint()
    already_done = len(playbooks)
    to_run       = PLAYBOOK_TOPICS[already_done:]

    for i, (topic, category, severity, team) in \
            enumerate(to_run, already_done + 1):

        if i % 20 == 1:
            print(f"Progress: {i}/{len(PLAYBOOK_TOPICS)} - {topic[:40]}")

        prompt   = build_playbook_prompt(
            topic, category, severity, team, i
        )
        response = call_ollama(prompt)
        parsed   = extract_json(response)

        if not parsed:
            parsed = {
                "playbook_id"    : f"FTF-PB-{i:03d}",
                "title"          : topic,
                "category"       : category,
                "severity"       : severity,
                "team"           : team,
                "trigger"        : "PagerDuty alert fired",
                "triage_steps"   : ["Assess scope", "Check dashboards",
                                    "Determine severity"],
                "response_phases": [
                    {"phase": "Detect",  "duration": "0-5 min",
                     "actions": ["Check Grafana"]},
                    {"phase": "Resolve", "duration": "5-30 min",
                     "actions": ["Apply fix", "Verify"]}
                ],
                "escalation_criteria": f"Escalate if not resolved in 30 mins",
                "rollback_procedure" : "Revert last change"
            }

        playbooks.append(parsed)

        if len(playbooks) % 25 == 0:
            with open(CHECKPOINT, 'w') as f:
                json.dump(playbooks, f, indent=2)
            print(f"Checkpoint: {len(playbooks)} saved")

        time.sleep(0.5)

    with open(OUTPUT, 'w') as f:
        json.dump(playbooks, f, indent=2)

    if CHECKPOINT.exists():
        CHECKPOINT.unlink()

    print(f"\nSaved {len(playbooks)} playbooks")


if __name__ == "__main__":
    main()