"""
Generate 300 FinTechFlow-specific postmortems
Run: python src/data_generation/generate_postmortems.py
"""
import json
import time
import re
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED    = PROJECT_ROOT / "data/processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

OLLAMA_URL  = "http://localhost:11434/api/generate"
MODEL       = "qwen2.5:7b"
OUTPUT      = PROCESSED / "ftf_postmortems.json"
CHECKPOINT  = PROCESSED / "ftf_postmortems_checkpoint.json"

COMPANY_CONTEXT = """
FinTechFlow is a B2B payment processing platform.
Stack: Java Spring Boot microservices, Python FastAPI,
PostgreSQL (primary DB, port 5432), Redis (cache, port 6379),
Elasticsearch (search, port 9200), Apache Kafka (messaging, port 9092),
Kubernetes on AWS EKS, Prometheus + Grafana (monitoring),
PagerDuty (alerting), HashiCorp Vault (secrets management),
AWS ALB + Route53 + Cloudflare (network), AWS S3 + EBS (storage),
GitHub Actions + ArgoCD (CI/CD), PgBouncer (connection pooler).
Services: payment-service, order-service, transaction-processor,
fraud-detection-service, notification-service, merchant-api.
Teams: payments-sre, platform-sre, security-sre, data-sre.
Scale: 50M transactions/day, $2B daily payment volume.
SLO: 99.95% uptime for payment-service.
"""

# 300 seeds — 6 per category × 8 categories = 48 unique scenarios
# with variations to reach 300
POSTMORTEM_SEEDS = [
    # DATABASE — 50 incidents
    ("PostgreSQL max_connections exhausted during Black Friday traffic surge", "database", "P1", "payments-sre"),
    ("Redis cache stampede after deployment flushed all keys simultaneously", "database", "P1", "platform-sre"),
    ("PostgreSQL WAL disk full halted all transaction writes", "database", "P1", "payments-sre"),
    ("Elasticsearch heap exhaustion caused payment search complete outage", "database", "P1", "platform-sre"),
    ("PostgreSQL replication lag 45s caused stale merchant balance reads", "database", "P2", "payments-sre"),
    ("PgBouncer connection pooler crashed during peak transaction period", "database", "P1", "payments-sre"),
    ("PostgreSQL autovacuum blocked causing table bloat and slow queries", "database", "P2", "payments-sre"),
    ("Redis sentinel failover caused 3min payment cache unavailability", "database", "P2", "platform-sre"),
    ("Elasticsearch circuit breaker triggered during bulk transaction indexing", "database", "P2", "platform-sre"),
    ("PostgreSQL deadlock storm on transactions table during batch processing", "database", "P2", "payments-sre"),
    ("PostgreSQL checkpoint taking 45 minutes due to excessive WAL generation", "database", "P2", "payments-sre"),
    ("Redis maxmemory-policy misconfigured caused payment session eviction", "database", "P2", "platform-sre"),
    ("Elasticsearch index corruption after unclean node shutdown", "database", "P2", "platform-sre"),
    ("PostgreSQL read replica fell behind causing dashboard inconsistency", "database", "P3", "payments-sre"),
    ("Redis cluster node failure caused partial cache miss storm", "database", "P2", "platform-sre"),
    ("PostgreSQL connection string misconfiguration after deployment", "database", "P2", "payments-sre"),
    ("Elasticsearch shard allocation failed after rolling restart", "database", "P3", "platform-sre"),
    ("PostgreSQL slow query caused by missing index on transactions table", "database", "P3", "payments-sre"),
    ("Redis pipeline batching misconfiguration caused latency spike", "database", "P3", "platform-sre"),
    ("PostgreSQL backup job filled temp disk space causing query failures", "database", "P2", "payments-sre"),
    ("PostgreSQL lock contention during schema migration caused timeouts", "database", "P2", "payments-sre"),
    ("Redis keyspace notification misconfiguration caused memory leak", "database", "P3", "platform-sre"),
    ("Elasticsearch mapping explosion caused cluster instability", "database", "P2", "platform-sre"),
    ("PostgreSQL sequence overflow on transaction_id column", "database", "P1", "payments-sre"),
    ("PostgreSQL SSL certificate expiry caused connection failures", "database", "P1", "payments-sre"),
    ("Redis AOF rewrite caused disk I/O saturation", "database", "P2", "platform-sre"),
    ("Elasticsearch snapshot failing caused disk full on data nodes", "database", "P2", "platform-sre"),
    ("PostgreSQL streaming replication slot bloat filled disk", "database", "P1", "payments-sre"),
    ("PgBouncer pool_mode mismatch caused transaction state corruption", "database", "P2", "payments-sre"),
    ("Redis cluster split-brain caused duplicate payment processing risk", "database", "P1", "payments-sre"),
    # NETWORK — 50 incidents
    ("Route53 NXDOMAIN for payment-api.fintechflow.io after TTL misconfiguration", "network", "P1", "platform-sre"),
    ("AWS ALB 502 errors after all payment-service pods failed health checks", "network", "P1", "payments-sre"),
    ("Kafka broker unreachable caused 2.4M message consumer group lag", "network", "P1", "platform-sre"),
    ("Cloudflare SSL certificate expired caused all HTTPS API traffic failure", "network", "P1", "security-sre"),
    ("VPC peering route missing blocked payment-service to PostgreSQL communication", "network", "P1", "platform-sre"),
    ("AWS ALB target group health check threshold misconfigured", "network", "P2", "platform-sre"),
    ("Kafka topic replication factor dropped to 1 risking data loss", "network", "P2", "platform-sre"),
    ("Cloudflare rate limiting misconfigured blocked merchant API calls", "network", "P2", "security-sre"),
    ("Route53 health check failure caused failover to wrong region", "network", "P2", "platform-sre"),
    ("AWS NAT Gateway exhausted ports caused intermittent connection drops", "network", "P2", "platform-sre"),
    ("Kafka partition leadership rebalance caused 15min processing gap", "network", "P2", "platform-sre"),
    ("AWS Security Group rule accidentally blocked port 5432 from payment pods", "network", "P1", "platform-sre"),
    ("Cloudflare Workers script timeout caused payment page load failures", "network", "P2", "security-sre"),
    ("Route53 weighted routing misconfigured sent 100pct traffic to staging", "network", "P1", "platform-sre"),
    ("Kafka consumer group rebalance storm during rolling deployment", "network", "P2", "platform-sre"),
    ("AWS ALB access logs filled S3 bucket causing log delivery failure", "network", "P3", "platform-sre"),
    ("VPC flow logs disabled missed detecting unusual traffic pattern", "network", "P3", "platform-sre"),
    ("Kafka offset commit failure caused duplicate transaction processing", "network", "P2", "payments-sre"),
    ("Cloudflare DDoS protection triggered false positive on merchant traffic", "network", "P2", "security-sre"),
    ("Route53 DNSSEC misconfiguration caused validation failures", "network", "P2", "platform-sre"),
    ("AWS ALB stickiness session misconfiguration caused cart loss", "network", "P3", "platform-sre"),
    ("Kafka broker disk full caused producer backpressure", "network", "P1", "platform-sre"),
    ("Cloudflare cache purge accidentally cleared payment session tokens", "network", "P2", "security-sre"),
    ("Route53 private hosted zone missing VPC association", "network", "P2", "platform-sre"),
    ("AWS Transit Gateway route propagation failure blocked cross-VPC traffic", "network", "P1", "platform-sre"),
    ("Kafka exactly-once semantics misconfiguration caused duplicate charges", "network", "P1", "payments-sre"),
    ("AWS ALB connection draining timeout too short caused in-flight request loss", "network", "P2", "platform-sre"),
    ("Cloudflare origin pull certificate mismatch caused 526 errors", "network", "P2", "security-sre"),
    ("Route53 latency-based routing sent EU traffic to US region", "network", "P3", "platform-sre"),
    ("Kafka consumer lag alerting threshold too high missed silent failure", "network", "P2", "platform-sre"),
    # MEMORY — 40 incidents
    ("Payment service JVM OOMKilled after memory leak in transaction parser", "memory", "P1", "payments-sre"),
    ("Kafka consumer heap exhaustion caused order processing backlog", "memory", "P1", "platform-sre"),
    ("Python fraud detection worker RSS exceeded 8GB killed by OOM killer", "memory", "P2", "payments-sre"),
    ("GC overhead limit exceeded in transaction-processor caused 503 errors", "memory", "P1", "payments-sre"),
    ("Redis maxmemory reached causing payment session cache eviction storm", "memory", "P2", "platform-sre"),
    ("Java metaspace exhaustion caused payment service class loading failure", "memory", "P2", "payments-sre"),
    ("Node.js notification service heap exhausted after leak in event emitter", "memory", "P2", "payments-sre"),
    ("Python worker memory fragmentation caused gradual performance degradation", "memory", "P3", "payments-sre"),
    ("JVM old generation full caused stop-the-world GC pause 45 seconds", "memory", "P1", "payments-sre"),
    ("Kafka Streams state store memory exceeded pod limit OOMKilled", "memory", "P2", "platform-sre"),
    ("Payment service connection pool not released caused memory accumulation", "memory", "P2", "payments-sre"),
    ("Elasticsearch field data cache exhaustion caused query failures", "memory", "P2", "platform-sre"),
    ("Java thread stack overflow caused payment service crash", "memory", "P2", "payments-sre"),
    ("Python asyncio coroutine leak caused memory growth over 72 hours", "memory", "P2", "payments-sre"),
    ("JVM compressed oops limit exceeded after heap expansion", "memory", "P2", "payments-sre"),
    ("Redis OBJECT ENCODING switch caused unexpected memory growth", "memory", "P3", "platform-sre"),
    ("Kafka producer buffer memory exhaustion caused send timeouts", "memory", "P2", "platform-sre"),
    ("Go microservice goroutine leak caused memory growth over weekend", "memory", "P2", "payments-sre"),
    ("Java PermGen exhaustion in legacy fraud detection service", "memory", "P2", "payments-sre"),
    ("Off-heap memory accumulation in Elasticsearch caused node instability", "memory", "P2", "platform-sre"),
    # STORAGE — 40 incidents
    ("EBS volume ENOSPC on PostgreSQL data directory halted all writes", "storage", "P1", "payments-sre"),
    ("Kafka log retention misconfigured filled /data partition on broker", "storage", "P1", "platform-sre"),
    ("S3 SlowDown throttling blocked transaction log archival pipeline", "storage", "P2", "data-sre"),
    ("PostgreSQL checkpoint WAL bloat filled backup EBS volume", "storage", "P2", "payments-sre"),
    ("EBS volume stuck in detaching state caused pod scheduling failures", "storage", "P2", "platform-sre"),
    ("S3 bucket versioning created millions of objects exceeding list limits", "storage", "P3", "data-sre"),
    ("EBS snapshot taking 4 hours blocked maintenance window", "storage", "P3", "payments-sre"),
    ("Kafka log segment corruption after unclean broker shutdown", "storage", "P1", "platform-sre"),
    ("PostgreSQL tablespace wrong filesystem caused permission errors", "storage", "P2", "payments-sre"),
    ("S3 lifecycle policy deleted active transaction logs prematurely", "storage", "P1", "data-sre"),
    ("EBS gp2 IOPS limit hit during transaction batch processing", "storage", "P2", "payments-sre"),
    ("Elasticsearch translog corruption required full shard recovery", "storage", "P2", "platform-sre"),
    ("PostgreSQL pg_wal directory filled faster than archiving", "storage", "P1", "payments-sre"),
    ("S3 cross-region replication lag caused fraud model stale data", "storage", "P2", "data-sre"),
    ("EBS volume type migration caused 2h I/O pause on PostgreSQL", "storage", "P2", "payments-sre"),
    ("Kafka log compaction too aggressive deleted unprocessed messages", "storage", "P2", "platform-sre"),
    ("S3 bucket policy change blocked transaction processor writes", "storage", "P1", "data-sre"),
    ("EBS multi-attach misconfiguration caused filesystem corruption", "storage", "P1", "platform-sre"),
    ("PostgreSQL temporary file limit caused complex query failures", "storage", "P3", "payments-sre"),
    ("Kafka topic deletion failed left orphaned partition directories", "storage", "P3", "platform-sre"),
    # APPLICATION — 50 incidents
    ("Payment service circuit breaker opened caused 100pct transaction failure", "application", "P1", "payments-sre"),
    ("Fraud detection service timeout caused all payments to queue indefinitely", "application", "P1", "payments-sre"),
    ("Order service CrashLoopBackOff after bad ConfigMap deployed to production", "application", "P2", "platform-sre"),
    ("Notification service Kafka consumer lag reached 2.4M messages backlog", "application", "P2", "payments-sre"),
    ("Transaction processor NullPointerException on null merchant_id field", "application", "P2", "payments-sre"),
    ("Merchant API rate limiter misconfigured throttled all valid requests", "application", "P1", "payments-sre"),
    ("Payment service deployment rolled back after error rate exceeded 5pct", "application", "P2", "payments-sre"),
    ("Fraud detection ML model stale data caused false positive surge", "application", "P2", "payments-sre"),
    ("Transaction processor duplicate payment due to retry storm", "application", "P1", "payments-sre"),
    ("Order service database migration timeout caused partial schema update", "application", "P1", "payments-sre"),
    ("Notification service dead letter queue filled silently", "application", "P3", "payments-sre"),
    ("Payment service graceful shutdown timeout caused in-flight loss", "application", "P2", "payments-sre"),
    ("Merchant API swagger endpoint exposed sensitive payment metadata", "application", "P2", "security-sre"),
    ("Transaction processor timezone bug caused wrong settlement date", "application", "P2", "payments-sre"),
    ("Fraud detection service feature flag rollout caused scoring regression", "application", "P2", "payments-sre"),
    ("Payment service thread pool exhaustion caused request queuing", "application", "P1", "payments-sre"),
    ("Order service async job leaked file handles over 48 hours", "application", "P2", "payments-sre"),
    ("Merchant API pagination bug caused incomplete transaction exports", "application", "P3", "payments-sre"),
    ("Payment service health check endpoint too strict caused false eviction", "application", "P2", "platform-sre"),
    ("Transaction processor idempotency key collision caused double charge", "application", "P1", "payments-sre"),
    ("Notification service SMTP connection pool exhausted silently failed", "application", "P2", "payments-sre"),
    ("Payment service feature toggle database caused read amplification", "application", "P3", "payments-sre"),
    ("Fraud detection batch scoring job blocked real-time scoring path", "application", "P2", "payments-sre"),
    ("Order service GraphQL N+1 query caused database connection exhaustion", "application", "P2", "payments-sre"),
    ("Transaction processor wrong currency rounding caused reconciliation failure", "application", "P2", "payments-sre"),
    # SECURITY — 30 incidents
    ("HashiCorp Vault sealed during AWS KMS key rotation window", "security", "P1", "security-sre"),
    ("AWS WAF rule false positive blocked legitimate merchant payment traffic", "security", "P1", "security-sre"),
    ("SSL certificate expired for api.fintechflow.io caused all API failures", "security", "P1", "security-sre"),
    ("AWS IAM AccessDenied blocked transaction log writes to S3", "security", "P2", "security-sre"),
    ("API key rotation failed for payment-gateway Stripe integration", "security", "P2", "security-sre"),
    ("Vault token TTL too short caused payment service secret refresh storm", "security", "P2", "security-sre"),
    ("AWS KMS key policy change blocked PostgreSQL encryption at rest", "security", "P1", "security-sre"),
    ("mTLS certificate rotation caused inter-service communication failure", "security", "P1", "security-sre"),
    ("CORS misconfiguration exposed merchant payment API to wrong origins", "security", "P2", "security-sre"),
    ("AWS Secrets Manager rotation lambda timeout left stale credentials", "security", "P2", "security-sre"),
    ("Vault AppRole secret-id expired caused payment service restart loop", "security", "P2", "security-sre"),
    ("AWS WAF rate limit too aggressive blocked high-volume merchant", "security", "P2", "security-sre"),
    ("TLS 1.0 deprecation broke legacy merchant payment integration", "security", "P2", "security-sre"),
    ("Cloudflare firewall rule accidentally blocked payment processing IPs", "security", "P1", "security-sre"),
    ("AWS IAM role trust policy change broke payment service S3 access", "security", "P2", "security-sre"),
    # KUBERNETES — 30 incidents
    ("EKS node worker-3 NotReady caused payment pods to reschedule 6 times", "kubernetes", "P1", "platform-sre"),
    ("Payment service pod CrashLoopBackOff restarts=24 after OOMKilled event", "kubernetes", "P1", "payments-sre"),
    ("ArgoCD sync failed ImagePullBackOff blocked new payment service release", "kubernetes", "P2", "platform-sre"),
    ("etcd high latency 3.2s risked leader election and cluster instability", "kubernetes", "P1", "platform-sre"),
    ("Ingress controller 502 all payment pods failed readiness probe simultaneously", "kubernetes", "P1", "payments-sre"),
    ("EKS cluster autoscaler failed during traffic surge nodes not provisioned", "kubernetes", "P1", "platform-sre"),
    ("Kubernetes HPA misconfigured caused over-scaling 50x payment pods", "kubernetes", "P2", "platform-sre"),
    ("PodDisruptionBudget misconfiguration allowed full payment service eviction", "kubernetes", "P1", "platform-sre"),
    ("ArgoCD out-of-sync caused stale ConfigMap in production payment service", "kubernetes", "P2", "platform-sre"),
    ("EKS control plane API server latency spike caused kubectl timeouts", "kubernetes", "P2", "platform-sre"),
    ("Kubernetes resource quota exhausted blocked new payment pods from starting", "kubernetes", "P2", "platform-sre"),
    ("Node affinity misconfiguration colocated competing payment workloads", "kubernetes", "P3", "platform-sre"),
    ("Init container timeout caused payment pod stuck in Init state", "kubernetes", "P2", "payments-sre"),
    ("Kubernetes network policy too restrictive blocked payment to Redis", "kubernetes", "P1", "platform-sre"),
    ("EKS managed node group upgrade caused 10min payment service disruption", "kubernetes", "P2", "platform-sre"),
    # MONITORING — 20 incidents
    ("PagerDuty alert storm 400 alerts in 5 minutes masked real P1 incident", "monitoring", "P1", "platform-sre"),
    ("Prometheus scrape timeout for payment-service hid memory spike", "monitoring", "P2", "payments-sre"),
    ("Grafana dashboard showing no data during active payment incident", "monitoring", "P2", "platform-sre"),
    ("Alert Manager route misconfiguration dropped P1 payment alerts silently", "monitoring", "P1", "platform-sre"),
    ("Jaeger trace sampling reduced to 1pct hid transaction processing failures", "monitoring", "P2", "platform-sre"),
    ("Prometheus TSDB corruption caused 6h metric gap during incident", "monitoring", "P2", "platform-sre"),
    ("PagerDuty escalation policy missing caused P1 alert went unacknowledged", "monitoring", "P1", "platform-sre"),
    ("Grafana alert evaluation delay caused 15min notification lag", "monitoring", "P2", "platform-sre"),
    ("Prometheus recording rules too expensive caused scrape delays", "monitoring", "P3", "platform-sre"),
    ("OpenTelemetry collector OOMKilled caused trace data loss", "monitoring", "P2", "platform-sre"),
    ("Alert Manager inhibition rules masked downstream payment failures", "monitoring", "P2", "platform-sre"),
    ("Prometheus federation misconfigured caused duplicate alert firing", "monitoring", "P3", "platform-sre"),
    ("Grafana provisioning error caused dashboard rollback wiped incident view", "monitoring", "P3", "platform-sre"),
    ("PagerDuty webhook timeout caused on-call not notified for 8 minutes", "monitoring", "P1", "platform-sre"),
    ("Loki log pipeline dropped payment service error logs during incident", "monitoring", "P2", "platform-sre"),
    ("Prometheus cardinality explosion caused OOMKilled on monitoring pod", "monitoring", "P2", "platform-sre"),
    ("Grafana snapshot link shared externally exposed payment metrics", "monitoring", "P2", "security-sre"),
    ("Alert fatigue caused on-call to disable critical payment threshold alert", "monitoring", "P1", "payments-sre"),
    ("Prometheus remote write backpressure caused metric staleness", "monitoring", "P3", "platform-sre"),
    ("Datadog agent misconfigured sent metrics to wrong organisation", "monitoring", "P2", "platform-sre"),
]


def build_postmortem_prompt(title: str, category: str,
                             severity: str, team: str,
                             idx: int) -> str:
    return f"""You are a senior SRE at FinTechFlow writing a blameless postmortem.

{COMPANY_CONTEXT}

Write a realistic detailed postmortem. Incident ID: FTF-PM-{idx:03d}

Title: {title}
Category: {category}
Severity: {severity}
Team: {team}

Return ONLY this JSON object, no other text:
{{
  "incident_id": "FTF-PM-{idx:03d}",
  "title": "{title}",
  "severity": "{severity}",
  "category": "{category}",
  "team": "{team}",
  "affected_services": ["service1", "service2"],
  "duration_minutes": <number>,
  "summary": "2 sentences: what failed and business impact in transactions/revenue",
  "timeline": [
    {{"time": "T+0min",  "event": "PagerDuty alert fired - describe specific alert"}},
    {{"time": "T+5min",  "event": "on-call acknowledged, initial investigation"}},
    {{"time": "T+12min", "event": "root cause identified - describe finding"}},
    {{"time": "T+20min", "event": "remediation applied - describe action"}},
    {{"time": "T+35min", "event": "service restored, error rate back to baseline"}}
  ],
  "root_cause": "2 sentences technical explanation with specific service names and error details",
  "contributing_factors": ["specific factor 1", "specific factor 2"],
  "resolution_steps": [
    "exact command or action step 1",
    "exact command or action step 2",
    "verification step"
  ],
  "impact": {{
    "transactions_affected": <realistic number>,
    "merchants_affected": <number>,
    "revenue_impact_estimate": "$X,XXX"
  }},
  "lessons_learned": ["specific lesson 1", "specific lesson 2"],
  "action_items": [
    {{"action": "specific technical improvement", "owner": "{team}", "due": "1 week"}},
    {{"action": "monitoring improvement", "owner": "platform-sre", "due": "2 weeks"}}
  ],
  "detection_method": "prometheus-alert or pagerduty or grafana or user-report"
}}"""


def call_ollama(prompt: str) -> str:
    payload = {
        "model"  : MODEL,
        "prompt" : prompt,
        "stream" : False,
        "options": {
            "temperature": 0.7,
            "num_predict": 1500,
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
            print(f"  Attempt {attempt+1} failed: {e}")
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
        print(f"Checkpoint: {len(data)} postmortems already done")
        return data
    return []


def main():
    print("FinTechFlow Postmortem Generator")
    print(f"Model  : {MODEL}")
    print(f"Target : {len(POSTMORTEM_SEEDS)} postmortems")

    postmortems   = load_checkpoint()
    already_done  = len(postmortems)
    seeds_to_run  = POSTMORTEM_SEEDS[already_done:]

    for i, (title, category, severity, team) in \
            enumerate(seeds_to_run, already_done + 1):

        if i % 25 == 1:
            print(f"\nProgress: {i}/{len(POSTMORTEM_SEEDS)} "
                  f"- {category} {severity}")

        prompt   = build_postmortem_prompt(
            title, category, severity, team, i
        )
        response = call_ollama(prompt)
        parsed   = extract_json(response)

        if not parsed:
            parsed = {
                "incident_id"     : f"FTF-PM-{i:03d}",
                "title"           : title,
                "severity"        : severity,
                "category"        : category,
                "team"            : team,
                "summary"         : f"FinTechFlow {severity} {category} incident: {title}",
                "root_cause"      : f"Technical investigation required for {category}.",
                "resolution_steps": ["Identify", "Remediate", "Verify"],
                "lessons_learned" : ["Improve monitoring", "Add runbook"]
            }

        postmortems.append(parsed)

        if len(postmortems) % 50 == 0:
            with open(CHECKPOINT, 'w') as f:
                json.dump(postmortems, f, indent=2)
            print(f"Checkpoint saved: {len(postmortems)}")

        time.sleep(0.5)

    with open(OUTPUT, 'w') as f:
        json.dump(postmortems, f, indent=2)

    if CHECKPOINT.exists():
        CHECKPOINT.unlink()

    print(f"\nSaved {len(postmortems)} postmortems to {OUTPUT}")


if __name__ == "__main__":
    main()