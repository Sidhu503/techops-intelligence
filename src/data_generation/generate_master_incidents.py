"""
Master Incident Dataset Generator
Generates 2000 synthetic IT incidents one at a time for reliability.
Run from project root: python src/data_generation/generate_master_incidents.py
"""

import json
import time
import re
from pathlib import Path

import requests
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED    = PROJECT_ROOT / "data/processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

OLLAMA_URL   = "http://localhost:11434/api/generate"
MODEL        = "qwen2.5:7b"
OUTPUT_FILE  = PROCESSED / "master_incidents.json"
TRAINING_CSV = PROCESSED / "training_data.csv"
CHECKPOINT   = PROCESSED / "master_incidents_checkpoint.json"

# Total 2000 incidents across 8 categories
GENERATION_PLAN = [
    ("database",    "P1", 100),
    ("database",    "P2", 100),
    ("database",    "P3", 100),
    ("network",     "P1", 100),
    ("network",     "P2", 100),
    ("network",     "P3", 100),
    ("memory",      "P1", 100),
    ("memory",      "P2", 100),
    ("memory",      "P3",  50),
    ("storage",     "P1",  80),
    ("storage",     "P2",  80),
    ("storage",     "P3",  40),
    ("application", "P1", 100),
    ("application", "P2", 100),
    ("application", "P3", 100),
    ("security",    "P1", 120),
    ("security",    "P2",  80),
    ("security",    "P3",  50),
    ("kubernetes",  "P1", 100),
    ("kubernetes",  "P2", 100),
    ("kubernetes",  "P3",  50),
    ("monitoring",  "P1",  50),
    ("monitoring",  "P2",  50),
    ("monitoring",  "P3",  50),
]

CATEGORY_SERVICES = {
    "database"   : ["PostgreSQL primary",
                    "Redis cache cluster",
                    "Elasticsearch cluster"],
    "network"    : ["AWS ALB", "Route53 DNS",
                    "Cloudflare CDN", "Kafka brokers",
                    "VPC peering"],
    "memory"     : ["Payment service JVM",
                    "Order service JVM",
                    "Python transaction worker",
                    "Kafka consumer"],
    "storage"    : ["EBS volume",
                    "S3 transaction logs",
                    "Kafka log storage",
                    "PostgreSQL WAL"],
    "application": ["Payment service",
                    "Order service",
                    "Transaction processor",
                    "Fraud detection service",
                    "Notification service"],
    "security"   : ["HashiCorp Vault",
                    "AWS WAF",
                    "AWS IAM",
                    "SSL certificate",
                    "API key management"],
    "kubernetes" : ["EKS cluster",
                    "Payment service pod",
                    "Order service pod",
                    "ArgoCD deployment",
                    "Ingress controller"],
    "monitoring" : ["Prometheus",
                    "Grafana",
                    "PagerDuty",
                    "Alert Manager"]
}

ERROR_EXAMPLES = {
    "database"   : ["ECONNREFUSED on port 5432",
                    "too many connections max_connections=200",
                    "deadlock detected on transactions table",
                    "WAL disk full on /dev/xvda1",
                    "replication lag 45s on read replica"],
    "network"    : ["ALB 502 Bad Gateway all targets unhealthy",
                    "Route53 NXDOMAIN for payment-api.fintechflow.io",
                    "Kafka broker unreachable ECONNREFUSED port 9092",
                    "Cloudflare 524 timeout upstream",
                    "VPC peering route missing"],
    "memory"     : ["OutOfMemoryError Java heap space payment-service",
                    "OOMKilled container payment-service limit=4Gi",
                    "GC overhead limit exceeded transaction-processor",
                    "Python worker RSS 8GB exceeds limit",
                    "Kafka consumer heap exhausted"],
    "storage"    : ["ENOSPC on /dev/xvda1 PostgreSQL data volume",
                    "S3 SlowDown throttling transaction-logs bucket",
                    "EBS volume stuck in detaching state",
                    "Kafka log retention causing disk full",
                    "PostgreSQL checkpoint taking 45 minutes"],
    "application": ["Payment service HTTP 500 on /api/v2/charge",
                    "Circuit breaker open fraud-detection-service",
                    "Transaction processor CrashLoopBackOff",
                    "Order service timeout after 30s downstream",
                    "Notification service queue depth 2.4M messages"],
    "security"   : ["Vault seal detected payment-service cannot read secrets",
                    "AWS IAM AccessDenied s3:PutObject transaction-logs",
                    "SSL certificate expired api.fintechflow.io",
                    "WAF blocking legitimate payment traffic false positive",
                    "API key rotation failed payment-gateway integration"],
    "kubernetes" : ["payment-service pod CrashLoopBackOff restarts=24",
                    "EKS node worker-3 NotReady kubelet unresponsive",
                    "ArgoCD sync failed payment-service ImagePullBackOff",
                    "Ingress controller 502 all payment pods unhealthy",
                    "etcd high latency 3.2s leader election at risk"],
    "monitoring" : ["PagerDuty alert storm 400 alerts in 5 minutes",
                    "Prometheus scrape timeout payment-service metrics",
                    "Grafana dashboard no data points for 30 minutes",
                    "Alert Manager route misconfigured P1 alerts dropped",
                    "Jaeger trace sampling reduced 100pct to 1pct"]
}

COMPANY_CONTEXT = """
Company: FinTechFlow — B2B payment processing platform
Stack: Java Spring Boot, Python FastAPI, PostgreSQL,
       Redis, Elasticsearch, Kafka, Kubernetes on AWS EKS,
       Prometheus, Grafana, HashiCorp Vault, Cloudflare
Scale: 50 million transactions per day, 500 engineers
"""

def build_prompt(category: str, severity: str,
                 idx: int, service: str, error: str) -> str:

    severity_context = {
        "P1": "complete outage, all payment processing halted, revenue impact $10k/minute",
        "P2": "significant degradation, some transactions failing, customer complaints rising",
        "P3": "minor issue, small subset of users affected, no revenue impact"
    }

    return f"""You are an SRE engineer at FinTechFlow writing an incident report.

Company context: {COMPANY_CONTEXT}

Generate exactly 1 incident report as a single JSON object.

category: {category}
severity: {severity} — {severity_context[severity]}
affected_service: {service}
error to include: {error}
incident number: {idx}

Return ONLY this JSON object, no other text:
{{
  "incident_id": "FTF-{idx:04d}",
  "title": "short 6-8 word title",
  "description": "2-3 sentences. What failed at FinTechFlow, what error appeared, what payment transactions were affected.",
  "severity": "{severity}",
  "category": "{category}",
  "affected_service": "{service}",
  "root_cause": "one sentence technical explanation specific to FinTechFlow stack",
  "resolution_steps": ["specific action 1", "specific action 2", "verification step"],
  "duration_minutes": {60 if severity == "P1" else 30 if severity == "P2" else 15},
  "lessons_learned": "one actionable improvement for FinTechFlow",
  "metadata": {{
    "environment": "production",
    "team": "payments-sre or platform-sre or security-sre",
    "detection_method": "prometheus-alert or pagerduty or grafana-dashboard"
  }}
}}"""

def call_ollama(prompt: str, max_retries: int = 3) -> str:
    payload = {
        "model"  : MODEL,
        "prompt" : prompt,
        "stream" : False,
        "options": {
            "temperature": 0.7,
            "num_predict": 600,   # single incident needs far less tokens
            "top_p"      : 0.9
        }
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(
                OLLAMA_URL,
                json    = payload,
                timeout = 120       # 2 mins per single incident is plenty
            )
            if response.status_code == 200:
                return response.json().get("response", "")
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            time.sleep(2)

    return ""


def extract_json_object(text: str) -> dict:
    """Extract single JSON object from model response."""
    text = text.strip()
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # Direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
        if isinstance(result, list) and result:
            return result[0]
    except Exception:
        pass

    # Find first JSON object in text
    match = re.search(r'\{.*?\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    return {}


def validate_incident(incident: dict, category: str,
                      severity: str, idx: int,
                      service: str) -> dict:
    defaults = {
        "incident_id"     : f"SYN-{idx:04d}",
        "title"           : f"{category.title()} {severity} incident",
        "description"     : f"A {severity} {category} incident on {service}.",
        "severity"        : severity,
        "category"        : category,
        "affected_service": service,
        "root_cause"      : f"Root cause under investigation.",
        "resolution_steps": ["Identify root cause",
                             "Apply fix", "Verify resolution"],
        "duration_minutes": 60 if severity == "P1" else 30 if severity == "P2" else 15,
        "lessons_learned" : "Improve monitoring for this service.",
        "metadata"        : {
            "environment"     : "production",
            "team"            : "platform",
            "detection_method": "monitoring"
        }
    }

    for key, val in defaults.items():
        if key not in incident or not incident[key]:
            incident[key] = val

    incident['severity'] = severity
    incident['category'] = category

    if isinstance(incident.get('resolution_steps'), str):
        incident['resolution_steps'] = [incident['resolution_steps']]

    return incident


def load_checkpoint() -> list:
    if CHECKPOINT.exists():
        with open(CHECKPOINT, 'r') as f:
            data = json.load(f)
        print(f"Checkpoint found: {len(data)} incidents already generated")
        return data
    return []


def save_checkpoint(incidents: list):
    with open(CHECKPOINT, 'w') as f:
        json.dump(incidents, f, indent=2)


def main():
    print("Master Incident Dataset Generator")
    print(f"Model     : {MODEL}")
    print(f"Strategy  : 1 incident per call (most reliable)")
    print(f"Target    : 2000 incidents")
    print(f"Output    : {OUTPUT_FILE}\n")

    all_incidents    = load_checkpoint()
    generated_so_far = len(all_incidents)

    # Build full list of (category, severity) for each incident
    work_items = []
    for category, severity, count in GENERATION_PLAN:
        services = CATEGORY_SERVICES[category]
        errors   = ERROR_EXAMPLES[category]
        for i in range(count):
            work_items.append({
                "category": category,
                "severity": severity,
                "service" : services[i % len(services)],
                "error"   : errors[i % len(errors)]
            })

    total = len(work_items)
    print(f"Total incidents to generate: {total}")
    print(f"Already done: {generated_so_far}\n")

    # Skip already completed items
    work_items = work_items[generated_so_far:]

    idx = generated_so_far

    for item in work_items:
        idx     += 1
        category = item['category']
        severity = item['severity']
        service  = item['service']
        error    = item['error']

        if idx % 50 == 0 or idx == 1:
            print(f"Progress: {idx}/{total} - "
                  f"{category} {severity}")

        prompt   = build_prompt(category, severity, idx, service, error)
        response = call_ollama(prompt)

        if response:
            parsed = extract_json_object(response)
        else:
            parsed = {}

        validated = validate_incident(
            parsed, category, severity, idx, service
        )
        all_incidents.append(validated)

        # Checkpoint every 100 incidents
        if len(all_incidents) % 100 == 0:
            save_checkpoint(all_incidents)
            print(f"Checkpoint saved: {len(all_incidents)} incidents")

    # Final save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_incidents, f, indent=2)
    print(f"\nDataset saved: {len(all_incidents)} incidents")

    # Build training CSV
    records = []
    for inc in all_incidents:
        text = (
            f"{inc.get('title', '')} "
            f"{inc.get('description', '')} "
            f"{inc.get('root_cause', '')}"
        ).strip()
        records.append({
            'text'    : text,
            'severity': inc.get('severity', 'P3'),
            'category': inc.get('category', 'application'),
            'source'  : 'synthetic_master'
        })

    df = pd.DataFrame(records)
    df.to_csv(TRAINING_CSV, index=False)
    print(f"Training CSV saved: {len(df)} rows")

    print(f"\nSeverity distribution:")
    print(df['severity'].value_counts().to_string())
    print(f"\nCategory distribution:")
    print(df['category'].value_counts().to_string())

    if CHECKPOINT.exists():
        CHECKPOINT.unlink()

    print("\nGeneration complete")


if __name__ == "__main__":
    main()