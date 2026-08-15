import json
import os
from langchain_community.llms import Ollama

os.makedirs("data/raw/text/postmortems", exist_ok=True)

llm = Ollama(
    model       = "qwen2.5:7b-instruct-q4_K_M",
    temperature = 0.1
)

# Real incident patterns from LogHub
INCIDENT_SEEDS = [
    # ── DATABASE INCIDENTS (10) ──────────────────────────────
    {
        "type"      : "database_connection_refused",
        "log_sample": "ERROR db.connection - Connection refused port 5432",
        "service"   : "PostgreSQL",
        "severity"  : "P1"
    },
    {
        "type"      : "database_connection_pool_exhausted",
        "log_sample": "WARN db.pool - Connection pool exhausted max=20 waiting=147",
        "service"   : "PostgreSQL",
        "severity"  : "P2"
    },
    {
        "type"      : "database_replication_lag",
        "log_sample": "WARN db.replication - Replica lag 45s exceeds threshold 10s",
        "service"   : "MySQL Replica",
        "severity"  : "P2"
    },
    {
        "type"      : "database_deadlock",
        "log_sample": "ERROR db.transaction - Deadlock detected rolled back transaction",
        "service"   : "PostgreSQL",
        "severity"  : "P2"
    },
    {
        "type"      : "database_corruption",
        "log_sample": "FATAL db.storage - Data page checksum mismatch block 4821",
        "service"   : "PostgreSQL",
        "severity"  : "P1"
    },
    {
        "type"      : "database_slow_query",
        "log_sample": "WARN db.query - Query exceeded 30s threshold table=orders rows=8M",
        "service"   : "MySQL",
        "severity"  : "P3"
    },
    {
        "type"      : "database_disk_full",
        "log_sample": "FATAL db.storage - Cannot extend relation base/16384 disk full",
        "service"   : "PostgreSQL",
        "severity"  : "P1"
    },
    {
        "type"      : "database_max_connections",
        "log_sample": "ERROR db - FATAL sorry too many clients already max_connections=100",
        "service"   : "PostgreSQL",
        "severity"  : "P1"
    },
    {
        "type"      : "database_backup_failure",
        "log_sample": "ERROR backup - pg_dump failed exit code 1 relation does not exist",
        "service"   : "PostgreSQL Backup",
        "severity"  : "P2"
    },
    {
        "type"      : "database_index_bloat",
        "log_sample": "WARN db.maintenance - Index bloat 89% on orders_idx vacuum required",
        "service"   : "PostgreSQL",
        "severity"  : "P3"
    },

    # ── MEMORY INCIDENTS (8) ─────────────────────────────────
    {
        "type"      : "memory_exhaustion_oom",
        "log_sample": "FATAL jvm - OutOfMemoryError Java heap space used=3.9GB max=4GB",
        "service"   : "Application Server",
        "severity"  : "P1"
    },
    {
        "type"      : "memory_leak_gradual",
        "log_sample": "WARN jvm.heap - Heap usage 87% GC overhead increasing over 6hrs",
        "service"   : "Payment Service",
        "severity"  : "P2"
    },
    {
        "type"      : "memory_swap_exhaustion",
        "log_sample": "WARN system - Swap usage 98% si=847 so=923 pages/sec",
        "service"   : "Linux Host",
        "severity"  : "P2"
    },
    {
        "type"      : "memory_gc_pressure",
        "log_sample": "ERROR jvm.gc - GC overhead limit exceeded 98% time in GC",
        "service"   : "Order Service",
        "severity"  : "P1"
    },
    {
        "type"      : "memory_container_oom_killed",
        "log_sample": "ERROR kubernetes - Container OOMKilled reason=OOMKilled exit=137",
        "service"   : "Kubernetes Pod",
        "severity"  : "P2"
    },
    {
        "type"      : "memory_shared_memory_exhaustion",
        "log_sample": "ERROR system - shmget failed errno=ENOSPC no space in shared memory",
        "service"   : "IPC System",
        "severity"  : "P2"
    },
    {
        "type"      : "memory_buffer_overflow",
        "log_sample": "FATAL app - Buffer overflow detected in request parser stack smash",
        "service"   : "API Gateway",
        "severity"  : "P1"
    },
    {
        "type"      : "memory_cache_eviction_storm",
        "log_sample": "WARN redis - Eviction rate 45000/sec maxmemory-policy=allkeys-lru",
        "service"   : "Redis Cache",
        "severity"  : "P2"
    },

    # ── NETWORK INCIDENTS (8) ────────────────────────────────
    {
        "type"      : "network_partition",
        "log_sample": "ERROR network - Unable to reach replica 10.0.0.5 timeout after 5s",
        "service"   : "Database Cluster",
        "severity"  : "P1"
    },
    {
        "type"      : "network_dns_resolution_failure",
        "log_sample": "ERROR dns - Resolution failed for payment-svc.internal NXDOMAIN",
        "service"   : "DNS Service",
        "severity"  : "P1"
    },
    {
        "type"      : "network_packet_loss",
        "log_sample": "WARN network - Packet loss 34% on eth0 retransmit rate elevated",
        "service"   : "Network Interface",
        "severity"  : "P2"
    },
    {
        "type"      : "network_bgp_route_flap",
        "log_sample": "ERROR bgp - Route flap detected peer=203.0.113.1 prefix withdrawn",
        "service"   : "BGP Router",
        "severity"  : "P1"
    },
    {
        "type"      : "network_load_balancer_health_check_failure",
        "log_sample": "ERROR lb - All backend targets unhealthy dropping connections",
        "service"   : "Load Balancer",
        "severity"  : "P1"
    },
    {
        "type"      : "network_ssl_handshake_failure",
        "log_sample": "ERROR ssl - Handshake failed peer certificate verify error depth=0",
        "service"   : "TLS Terminator",
        "severity"  : "P2"
    },
    {
        "type"      : "network_bandwidth_saturation",
        "log_sample": "WARN network - Interface eth0 utilization 99% TX=940Mbps max=1Gbps",
        "service"   : "Network Interface",
        "severity"  : "P2"
    },
    {
        "type"      : "network_firewall_rule_misconfiguration",
        "log_sample": "ERROR firewall - Dropping packets from 10.0.1.0/24 no matching rule",
        "service"   : "Firewall",
        "severity"  : "P1"
    },

    # ── STORAGE INCIDENTS (6) ────────────────────────────────
    {
        "type"      : "disk_full_var_log",
        "log_sample": "ERROR storage - /var/log filesystem 100% write failed ENOSPC",
        "service"   : "Log Storage",
        "severity"  : "P2"
    },
    {
        "type"      : "disk_full_data_volume",
        "log_sample": "FATAL storage - /data filesystem 100% database writes failing",
        "service"   : "Data Volume",
        "severity"  : "P1"
    },
    {
        "type"      : "disk_io_saturation",
        "log_sample": "WARN disk - I/O wait 89% on /dev/sda1 await=245ms util=99%",
        "service"   : "Block Storage",
        "severity"  : "P2"
    },
    {
        "type"      : "storage_raid_degraded",
        "log_sample": "ERROR raid - Array degraded 1 disk failed rebuilding remaining disk",
        "service"   : "RAID Array",
        "severity"  : "P1"
    },
    {
        "type"      : "storage_nfs_mount_failure",
        "log_sample": "ERROR nfs - Mount failed for nas01:/data stale file handle",
        "service"   : "NFS Storage",
        "severity"  : "P2"
    },
    {
        "type"      : "storage_s3_throttling",
        "log_sample": "WARN s3 - SlowDown rate exceeded retrying with backoff attempt=5",
        "service"   : "AWS S3",
        "severity"  : "P3"
    },

    # ── APPLICATION INCIDENTS (8) ────────────────────────────
    {
        "type"      : "api_timeout_cascade",
        "log_sample": "ERROR http - GET /api/orders timeout 30000ms circuit breaker open",
        "service"   : "Order Service",
        "severity"  : "P1"
    },
    {
        "type"      : "service_crash_segfault",
        "log_sample": "FATAL app - Segmentation fault core dumped signal=11 SIGSEGV",
        "service"   : "Payment Service",
        "severity"  : "P1"
    },
    {
        "type"      : "deployment_rollout_failure",
        "log_sample": "ERROR deploy - Rollout failed health check timeout new pods CrashLoop",
        "service"   : "Kubernetes Deployment",
        "severity"  : "P2"
    },
    {
        "type"      : "queue_consumer_lag",
        "log_sample": "WARN kafka - Consumer lag 2.4M messages topic=orders partition=0",
        "service"   : "Kafka Consumer",
        "severity"  : "P2"
    },
    {
        "type"      : "cache_stampede",
        "log_sample": "ERROR redis - Cache miss storm 45000 req/s DB overwhelmed",
        "service"   : "Cache Layer",
        "severity"  : "P1"
    },
    {
        "type"      : "rate_limiter_misconfiguration",
        "log_sample": "ERROR gateway - Rate limit 429 all requests blocked threshold=0",
        "service"   : "API Gateway",
        "severity"  : "P1"
    },
    {
        "type"      : "third_party_api_outage",
        "log_sample": "ERROR client - Stripe API timeout after 10s payment processing halted",
        "service"   : "Payment Integration",
        "severity"  : "P2"
    },
    {
        "type"      : "config_map_missing",
        "log_sample": "FATAL app - ConfigMap payment-config not found pod crashlooping",
        "service"   : "Kubernetes Config",
        "severity"  : "P2"
    },

    # ── SECURITY INCIDENTS (6) ───────────────────────────────
    {
        "type"      : "ssl_certificate_expired",
        "log_sample": "ERROR ssl - Certificate expired for api.company.com 30 days ago",
        "service"   : "API Gateway",
        "severity"  : "P1"
    },
    {
        "type"      : "authentication_service_down",
        "log_sample": "ERROR auth - Token validation unreachable all logins failing",
        "service"   : "Auth Service",
        "severity"  : "P1"
    },
    {
        "type"      : "ddos_attack_detected",
        "log_sample": "WARN security - Anomalous traffic 4.2M req/s from 847 IPs blocked",
        "service"   : "WAF",
        "severity"  : "P1"
    },
    {
        "type"      : "secret_rotation_failure",
        "log_sample": "ERROR vault - Secret rotation failed db-password stale credential",
        "service"   : "HashiCorp Vault",
        "severity"  : "P2"
    },
    {
        "type"      : "iam_permission_denied",
        "log_sample": "ERROR aws - AccessDenied s3:PutObject arn:aws:iam::123:role/app",
        "service"   : "AWS IAM",
        "severity"  : "P2"
    },
    {
        "type"      : "api_key_compromised",
        "log_sample": "WARN security - API key used from 47 countries anomaly detected",
        "service"   : "API Security",
        "severity"  : "P1"
    },

    # ── KUBERNETES / INFRASTRUCTURE (8) ─────────────────────
    {
        "type"      : "kubernetes_node_notready",
        "log_sample": "ERROR k8s - Node worker-03 NotReady kubelet stopped posting status",
        "service"   : "Kubernetes Node",
        "severity"  : "P2"
    },
    {
        "type"      : "kubernetes_pod_crashloop",
        "log_sample": "ERROR k8s - Pod payment-7d9f CrashLoopBackOff restarts=24",
        "service"   : "Kubernetes Pod",
        "severity"  : "P2"
    },
    {
        "type"      : "kubernetes_pvc_pending",
        "log_sample": "WARN k8s - PVC data-volume Pending no PersistentVolume available",
        "service"   : "Kubernetes Storage",
        "severity"  : "P2"
    },
    {
        "type"      : "kubernetes_etcd_high_latency",
        "log_sample": "WARN etcd - Apply took too long 2.5s threshold=1s leader election risk",
        "service"   : "etcd Cluster",
        "severity"  : "P1"
    },
    {
        "type"      : "kubernetes_resource_quota_exceeded",
        "log_sample": "ERROR k8s - Exceeded quota cpu=0/4 memory=0/8Gi pods cannot schedule",
        "service"   : "Kubernetes Scheduler",
        "severity"  : "P2"
    },
    {
        "type"      : "kubernetes_image_pull_failure",
        "log_sample": "ERROR k8s - ErrImagePull registry.company.com/app:v2.1 unauthorized",
        "service"   : "Container Registry",
        "severity"  : "P2"
    },
    {
        "type"      : "kubernetes_hpa_misconfiguration",
        "log_sample": "WARN k8s - HPA unable to scale metrics server unavailable",
        "service"   : "Kubernetes HPA",
        "severity"  : "P3"
    },
    {
        "type"      : "kubernetes_ingress_misconfiguration",
        "log_sample": "ERROR ingress - 502 Bad Gateway upstream connect error all pods down",
        "service"   : "Nginx Ingress",
        "severity"  : "P1"
    },

    # ── MONITORING / OBSERVABILITY (4) ───────────────────────
    {
        "type"      : "monitoring_alert_storm",
        "log_sample": "WARN pagerduty - 847 alerts fired in 60s alert storm detected",
        "service"   : "PagerDuty",
        "severity"  : "P3"
    },
    {
        "type"      : "log_pipeline_failure",
        "log_sample": "ERROR logstash - Pipeline stalled input queue full 100000 events",
        "service"   : "Log Pipeline",
        "severity"  : "P2"
    },
    {
        "type"      : "metrics_collection_gap",
        "log_sample": "WARN prometheus - Scrape failed target=node-exporter-03 timeout",
        "service"   : "Prometheus",
        "severity"  : "P3"
    },
    {
        "type"      : "tracing_backend_overload",
        "log_sample": "WARN jaeger - Spans dropped sampling rate reduced 100% to 10%",
        "service"   : "Jaeger Tracing",
        "severity"  : "P3"
    }
]

PROMPT_TEMPLATE = """You are a senior SRE writing a structured incident postmortem.
Generate a realistic, detailed postmortem in JSON format only.
No markdown, no explanation, just valid JSON.

Incident seed:
- Type: {incident_type}
- Log sample: {log_sample}
- Affected service: {service}
- Severity: {severity}

Generate JSON with exactly these fields:
{{
    "incident_id": "INC-XXXX",
    "title": "brief title",
    "severity": "{severity}",
    "category": "{incident_type}",
    "affected_service": "{service}",
    "duration_minutes": <number>,
    "detection_time": "HH:MM UTC",
    "resolution_time": "HH:MM UTC",
    "summary": "2-3 sentence summary of what happened",
    "timeline": [
        {{"time": "HH:MM", "event": "description"}},
        {{"time": "HH:MM", "event": "description"}},
        {{"time": "HH:MM", "event": "description"}},
        {{"time": "HH:MM", "event": "description"}},
        {{"time": "HH:MM", "event": "description"}}
    ],
    "root_cause": "detailed technical root cause explanation",
    "contributing_factors": ["factor1", "factor2", "factor3"],
    "resolution_steps": [
        "step 1 taken to resolve",
        "step 2 taken to resolve",
        "step 3 taken to resolve"
    ],
    "impact": {{
        "users_affected": <number>,
        "revenue_impact": "estimated impact",
        "services_affected": ["service1", "service2"]
    }},
    "lessons_learned": ["lesson1", "lesson2", "lesson3"],
    "action_items": [
        {{"action": "description", "owner": "team", "due": "timeframe"}},
        {{"action": "description", "owner": "team", "due": "timeframe"}}
    ],
    "detection_method": "how was this detected",
    "prevention": "how to prevent recurrence"
}}"""

postmortems = []
for i, seed in enumerate(INCIDENT_SEEDS):
    print(f"Generating postmortem {i+1}/{len(INCIDENT_SEEDS)}: {seed['type']}")

    prompt = PROMPT_TEMPLATE.format(
        incident_type = seed['type'],
        log_sample    = seed['log_sample'],
        service       = seed['service'],
        severity      = seed['severity']
    )

    response = llm.invoke(prompt)

    try:
        # Clean response and parse JSON
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        postmortem = json.loads(clean)
        postmortem['source'] = 'generated_from_real_log_patterns'
        postmortem['seed_log'] = seed['log_sample']
        postmortems.append(postmortem)
        print(f"  ✓ Generated: {postmortem.get('title', 'untitled')}")

    except json.JSONDecodeError as e:
        print(f"  ⚠️  Parse error on {seed['type']}: {e}")
        print(f"  Raw response: {response[:200]}")

# Save all postmortems
output_path = "data/raw/text/postmortems/postmortems.json"
with open(output_path, "w") as f:
    json.dump(postmortems, f, indent=2)

print(f"\n✅ Generated {len(postmortems)} postmortems")
print(f"   Saved to: {output_path}")

# Also save individual files for easier inspection
for pm in postmortems:
    fname = f"data/raw/text/postmortems/{pm['incident_id']}_{pm['category']}.json"
    with open(fname, "w") as f:
        json.dump(pm, f, indent=2)

print(f"   Individual files saved to data/raw/text/postmortems/")