"""
Generate 200 FinTechFlow SRE QA pairs
Run: python src/data_generation/generate_sre_qa.py
"""
import json
import time
import re
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED    = PROJECT_ROOT / "data/processed"
OUTPUT       = PROCESSED / "ftf_sre_qa.json"
CHECKPOINT   = PROCESSED / "ftf_sre_qa_checkpoint.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "qwen2.5:7b"

QA_TOPICS = [
    # INCIDENT RESPONSE — 30
    ("What are the first 5 steps when PagerDuty fires for payment-service?", "incident_response"),
    ("How do I declare a P1 major incident at FinTechFlow?", "incident_response"),
    ("What is the incident severity classification at FinTechFlow?", "incident_response"),
    ("How do I run an incident war room at FinTechFlow?", "incident_response"),
    ("When should I escalate from P2 to P1?", "incident_response"),
    ("How do I communicate with merchants during a P1 outage?", "incident_response"),
    ("What is the FinTechFlow incident response checklist?", "incident_response"),
    ("How do I assign roles during a major incident?", "incident_response"),
    ("What metrics should I check first during a payment outage?", "incident_response"),
    ("How do I determine blast radius of a payment incident?", "incident_response"),
    ("What is the SLO for payment-service at FinTechFlow?", "incident_response"),
    ("How do I calculate MTTR for our payment incidents?", "incident_response"),
    ("When should I page the on-call database engineer?", "incident_response"),
    ("How do I write a preliminary incident update for merchants?", "incident_response"),
    ("What is the escalation path for P1 security incidents?", "incident_response"),
    ("How do I handle a simultaneous P1 and P2 incident?", "incident_response"),
    ("What Grafana dashboards should I open first during an incident?", "incident_response"),
    ("How long before I must send a merchant-facing update?", "incident_response"),
    ("When is it safe to close a P1 incident?", "incident_response"),
    ("How do I hand off an ongoing incident at shift change?", "incident_response"),
    ("What PagerDuty runbook should I follow for payment-service?", "incident_response"),
    ("How do I silence a PagerDuty alert storm safely?", "incident_response"),
    ("What is the FinTechFlow war room bridge number?", "incident_response"),
    ("How do I coordinate with the security team during an incident?", "incident_response"),
    ("What is the rollback procedure for a bad payment-service deployment?", "incident_response"),
    ("How do I assess if an incident requires executive notification?", "incident_response"),
    ("What tools do I use to correlate logs during an incident?", "incident_response"),
    ("How do I open a status page incident for FinTechFlow?", "incident_response"),
    ("What is the standard incident timeline format at FinTechFlow?", "incident_response"),
    ("How do I preserve evidence during a security incident?", "incident_response"),
    # DATABASE — 30
    ("How do I check PostgreSQL connection pool status at FinTechFlow?", "database"),
    ("What command shows active connections in PostgreSQL?", "database"),
    ("How do I safely kill idle PostgreSQL connections?", "database"),
    ("What is the max_connections limit for our PostgreSQL cluster?", "database"),
    ("How do I check PgBouncer pool usage?", "database"),
    ("What causes PostgreSQL replication lag at FinTechFlow?", "database"),
    ("How do I check disk usage on PostgreSQL EBS volume?", "database"),
    ("What is the procedure when PostgreSQL WAL fills up?", "database"),
    ("How do I check for PostgreSQL deadlocks on transactions table?", "database"),
    ("How do I identify slow queries in PostgreSQL?", "database"),
    ("What is the Redis eviction policy at FinTechFlow?", "database"),
    ("How do I check Redis memory usage and fragmentation?", "database"),
    ("How do I flush Redis cache safely without causing stampede?", "database"),
    ("What is the Elasticsearch heap size for our cluster?", "database"),
    ("How do I check Elasticsearch circuit breaker status?", "database"),
    ("How do I identify which Elasticsearch query is consuming most memory?", "database"),
    ("How do I recover an Elasticsearch red cluster status?", "database"),
    ("What is PostgreSQL autovacuum configuration at FinTechFlow?", "database"),
    ("How do I check PostgreSQL table bloat?", "database"),
    ("How do I increase PostgreSQL max_connections temporarily?", "database"),
    ("What is the Redis sentinel configuration at FinTechFlow?", "database"),
    ("How do I trigger Redis failover manually?", "database"),
    ("What are the PostgreSQL monitoring alerts we have in Prometheus?", "database"),
    ("How do I check PostgreSQL streaming replication slot lag?", "database"),
    ("What is the procedure for PostgreSQL point-in-time recovery?", "database"),
    ("How do I check Elasticsearch shard allocation status?", "database"),
    ("What command shows PostgreSQL checkpoint frequency?", "database"),
    ("How do I rotate PostgreSQL credentials safely?", "database"),
    ("What is PgBouncer pool_mode at FinTechFlow and why?", "database"),
    ("How do I verify PostgreSQL backup integrity?", "database"),
    # NETWORK — 25
    ("How do I check ALB target health in AWS console?", "network"),
    ("What do I do when Route53 returns NXDOMAIN for payment-api?", "network"),
    ("How do I check Kafka broker status?", "network"),
    ("What command shows Kafka consumer group lag?", "network"),
    ("How do I reduce Kafka consumer lag quickly?", "network"),
    ("How do I check Cloudflare SSL certificate expiry?", "network"),
    ("What is the Cloudflare WAF configuration for payment traffic?", "network"),
    ("How do I check VPC peering routes in AWS?", "network"),
    ("What is the AWS NAT Gateway limits for FinTechFlow?", "network"),
    ("How do I check AWS Security Group rules for payment-service?", "network"),
    ("How do I add a Kafka consumer to reduce lag quickly?", "network"),
    ("What is the Kafka replication factor for payment topics?", "network"),
    ("How do I check if ALB access logs are being delivered?", "network"),
    ("What is the Route53 health check configuration?", "network"),
    ("How do I check AWS Transit Gateway route table?", "network"),
    ("What is the Kafka retention policy for payment events?", "network"),
    ("How do I check Cloudflare DDoS protection status?", "network"),
    ("How do I verify DNS propagation after Route53 change?", "network"),
    ("What is the ALB idle timeout for payment-service?", "network"),
    ("How do I check Kafka partition distribution?", "network"),
    ("How do I temporarily disable Cloudflare WAF rule?", "network"),
    ("What is the VPC CIDR range for FinTechFlow production?", "network"),
    ("How do I check inter-service network latency in EKS?", "network"),
    ("What is the Kafka exactly-once semantics configuration?", "network"),
    ("How do I check AWS NLB connection tracking limits?", "network"),
    # KUBERNETES — 25
    ("How do I check why a pod is in CrashLoopBackOff?", "kubernetes"),
    ("What command shows pod resource usage in EKS?", "kubernetes"),
    ("How do I safely restart payment-service pods?", "kubernetes"),
    ("What do I do when an EKS node is NotReady?", "kubernetes"),
    ("How do I roll back a bad ArgoCD deployment?", "kubernetes"),
    ("How do I check etcd cluster health?", "kubernetes"),
    ("What is the HPA configuration for payment-service?", "kubernetes"),
    ("How do I cordon and drain an EKS node safely?", "kubernetes"),
    ("How do I check pod resource limits and requests?", "kubernetes"),
    ("What is the PodDisruptionBudget for payment-service?", "kubernetes"),
    ("How do I debug an ImagePullBackOff error?", "kubernetes"),
    ("How do I check ArgoCD sync status?", "kubernetes"),
    ("What is the EKS cluster autoscaler configuration?", "kubernetes"),
    ("How do I check Kubernetes network policies for payment pods?", "kubernetes"),
    ("How do I force delete a stuck terminating pod?", "kubernetes"),
    ("What is the readiness probe configuration for payment-service?", "kubernetes"),
    ("How do I check EKS control plane logs?", "kubernetes"),
    ("How do I increase pod memory limit temporarily?", "kubernetes"),
    ("What is the namespace structure at FinTechFlow?", "kubernetes"),
    ("How do I check Kubernetes events for a deployment?", "kubernetes"),
    ("How do I view ArgoCD deployment history?", "kubernetes"),
    ("What is the node selector for payment workloads?", "kubernetes"),
    ("How do I check cluster resource utilisation?", "kubernetes"),
    ("How do I debug a pod stuck in Init state?", "kubernetes"),
    ("What is the EKS version at FinTechFlow and upgrade policy?", "kubernetes"),
    # SECURITY — 20
    ("How do I unseal HashiCorp Vault at FinTechFlow?", "security"),
    ("What do I do when AWS WAF blocks legitimate payments?", "security"),
    ("How do I renew an expired SSL certificate in our stack?", "security"),
    ("What is the Vault token TTL for payment-service?", "security"),
    ("How do I check AWS IAM AccessDenied root cause?", "security"),
    ("How do I rotate API keys for payment-gateway integration?", "security"),
    ("What is the mTLS configuration between FinTechFlow services?", "security"),
    ("How do I check Vault audit logs for access issues?", "security"),
    ("How do I temporarily disable a WAF rule safely?", "security"),
    ("What is the AWS KMS key rotation schedule?", "security"),
    ("How do I check Cloudflare firewall event logs?", "security"),
    ("What is the AWS Secrets Manager rotation procedure?", "security"),
    ("How do I verify Vault is fully operational after unseal?", "security"),
    ("What is the IAM role for payment-service?", "security"),
    ("How do I rotate database credentials in Vault?", "security"),
    ("What is the certificate authority for FinTechFlow mTLS?", "security"),
    ("How do I check for expired certificates across all services?", "security"),
    ("What is the Cloudflare zone ID for fintechflow.io?", "security"),
    ("How do I add a WAF whitelist rule for a merchant IP?", "security"),
    ("What is the procedure for a suspected security breach?", "security"),
    # MONITORING — 20
    ("How do I silence a PagerDuty alert without missing real alerts?", "monitoring"),
    ("What Prometheus queries show payment service health?", "monitoring"),
    ("How do I check if Prometheus is scraping payment-service metrics?", "monitoring"),
    ("What Grafana dashboard shows the payment service SLO?", "monitoring"),
    ("How do I create a new Prometheus alert rule?", "monitoring"),
    ("What is the Alert Manager routing configuration?", "monitoring"),
    ("How do I check Jaeger traces for slow transactions?", "monitoring"),
    ("How do I verify Grafana is showing real-time data?", "monitoring"),
    ("What is the Prometheus retention period at FinTechFlow?", "monitoring"),
    ("How do I check OpenTelemetry collector status?", "monitoring"),
    ("What are the SLO burn rate alert thresholds?", "monitoring"),
    ("How do I set up a temporary alert for an incident?", "monitoring"),
    ("How do I check Loki log pipeline health?", "monitoring"),
    ("What is the Grafana oncall escalation chain?", "monitoring"),
    ("How do I check Prometheus TSDB health?", "monitoring"),
    ("How do I add a new Grafana dashboard panel?", "monitoring"),
    ("What is the PagerDuty service ID for payment-service?", "monitoring"),
    ("How do I check metric cardinality in Prometheus?", "monitoring"),
    ("How do I correlate metrics and logs during an incident?", "monitoring"),
    ("What are the top 5 dashboards every FTF SRE should know?", "monitoring"),
    # SRE CONCEPTS — 20
    ("What is FinTechFlow error budget policy for payment-service?", "reliability"),
    ("How do we calculate SLO for payment processing at FinTechFlow?", "reliability"),
    ("What is the MTTR target for P1 incidents?", "reliability"),
    ("How do we measure toil at FinTechFlow?", "reliability"),
    ("What is the capacity planning process for payment peaks?", "capacity"),
    ("How do we forecast Kafka partition growth?", "capacity"),
    ("When should we scale PostgreSQL at FinTechFlow?", "capacity"),
    ("What is the auto-scaling policy for payment-service pods?", "capacity"),
    ("How do we conduct chaos engineering at FinTechFlow?", "reliability"),
    ("What is the change freeze policy during peak payment periods?", "reliability"),
    ("How do we write a blameless postmortem at FinTechFlow?", "postmortem"),
    ("What are the required sections in a FinTechFlow postmortem?", "postmortem"),
    ("How do we track postmortem action items?", "postmortem"),
    ("What is the postmortem review schedule?", "postmortem"),
    ("How long after a P1 must the postmortem be complete?", "postmortem"),
    ("What is the FinTechFlow on-call rotation schedule?", "reliability"),
    ("How do we define and measure reliability at FinTechFlow?", "reliability"),
    ("What is the deployment frequency target at FinTechFlow?", "reliability"),
    ("How do we handle error budget exhaustion?", "reliability"),
    ("What is the runbook review cadence at FinTechFlow?", "reliability"),
]


def build_qa_prompt(question: str, category: str, idx: int) -> str:
    return f"""You are a senior SRE at FinTechFlow answering a teammate's question.

FinTechFlow: B2B payment processor, 50M transactions/day, $2B daily volume.
Stack: Java Spring Boot, Python FastAPI, PostgreSQL (port 5432), Redis (port 6379),
Kafka (port 9092), Kubernetes EKS, HashiCorp Vault, Prometheus, Grafana, PagerDuty,
AWS ALB, Route53, Cloudflare, ArgoCD, GitHub Actions.
Services: payment-service, order-service, transaction-processor,
fraud-detection-service, notification-service, merchant-api.
SLO: 99.95% uptime for payment-service. P1 MTTR target: 30 minutes.

Question: {question}
Category: {category}
QA ID: FTF-QA-{idx:03d}

Return ONLY this JSON object:
{{
  "qa_id": "FTF-QA-{idx:03d}",
  "question": "{question}",
  "category": "{category}",
  "answer": "detailed 3-5 sentence answer with specific commands, thresholds, service names, and procedures for FinTechFlow",
  "key_commands": [
    "exact command 1 with flags",
    "exact command 2"
  ],
  "related_runbook": "FTF-RB-XX if applicable otherwise null",
  "escalation_threshold": "specific condition that makes this a P1 at FinTechFlow"
}}"""


def call_ollama(prompt: str) -> str:
    payload = {
        "model"  : MODEL,
        "prompt" : prompt,
        "stream" : False,
        "options": {
            "temperature": 0.6,
            "num_predict": 900,
            "top_p"      : 0.9
        }
    }
    for attempt in range(3):
        try:
            r = requests.post(
                OLLAMA_URL, json=payload, timeout=120
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
        print(f"Checkpoint: {len(data)} QA pairs done")
        return data
    return []


def main():
    print("FinTechFlow SRE QA Generator")
    print(f"Target: {len(QA_TOPICS)} QA pairs")

    qa_pairs     = load_checkpoint()
    already_done = len(qa_pairs)
    to_run       = QA_TOPICS[already_done:]

    for i, (question, category) in \
            enumerate(to_run, already_done + 1):

        if i % 25 == 1:
            print(f"Progress: {i}/{len(QA_TOPICS)} - {category}")

        prompt   = build_qa_prompt(question, category, i)
        response = call_ollama(prompt)
        parsed   = extract_json(response)

        if not parsed:
            parsed = {
                "qa_id"   : f"FTF-QA-{i:03d}",
                "question": question,
                "category": category,
                "answer"  : f"Refer to FinTechFlow {category} runbook.",
                "key_commands"          : [],
                "escalation_threshold"  : "P1 when service SLO breached"
            }

        qa_pairs.append(parsed)

        if len(qa_pairs) % 50 == 0:
            with open(CHECKPOINT, 'w') as f:
                json.dump(qa_pairs, f, indent=2)
            print(f"Checkpoint: {len(qa_pairs)} saved")

        time.sleep(0.5)

    with open(OUTPUT, 'w') as f:
        json.dump(qa_pairs, f, indent=2)

    if CHECKPOINT.exists():
        CHECKPOINT.unlink()

    print(f"\nSaved {len(qa_pairs)} QA pairs")


if __name__ == "__main__":
    main()