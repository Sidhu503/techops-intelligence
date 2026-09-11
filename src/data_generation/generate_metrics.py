"""
Generate synthetic system metrics for FinTechFlow services
Annotated with incident windows for realistic anomaly detection
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_TABULAR  = PROJECT_ROOT / "data/raw/tabular/fintechflow"
RAW_TABULAR.mkdir(parents=True, exist_ok=True)

np.random.seed(42)

SERVICES = {
    "payment-service"      : {"cpu_base": 35, "mem_base": 60,
                               "disk_base": 45, "req_base": 1200},
    "order-service"        : {"cpu_base": 25, "mem_base": 50,
                               "disk_base": 30, "req_base": 800},
    "transaction-processor": {"cpu_base": 55, "mem_base": 70,
                               "disk_base": 60, "req_base": 2000},
    "fraud-detection"      : {"cpu_base": 45, "mem_base": 65,
                               "disk_base": 35, "req_base": 1500},
    "postgresql-primary"   : {"cpu_base": 30, "mem_base": 75,
                               "disk_base": 70, "req_base": 5000},
}

# Known incident windows for annotation
INCIDENT_WINDOWS = [
    {"service": "payment-service",
     "start_offset_hours": 24, "duration_hours": 1,
     "type": "memory_spike", "severity": "P1"},
    {"service": "postgresql-primary",
     "start_offset_hours": 48, "duration_hours": 2,
     "type": "disk_full", "severity": "P1"},
    {"service": "transaction-processor",
     "start_offset_hours": 72, "duration_hours": 0.5,
     "type": "cpu_spike", "severity": "P2"},
    {"service": "fraud-detection",
     "start_offset_hours": 96, "duration_hours": 1.5,
     "type": "memory_leak", "severity": "P2"},
    {"service": "order-service",
     "start_offset_hours": 120, "duration_hours": 0.5,
     "type": "cpu_spike", "severity": "P3"},
]


def generate_service_metrics(
    service_name: str,
    base_metrics: dict,
    days: int = 7
) -> pd.DataFrame:
    periods   = days * 24 * 12  # every 5 minutes
    start     = datetime(2024, 1, 1)
    timestamps = [
        start + timedelta(minutes=5*i)
        for i in range(periods)
    ]

    cpu    = np.random.normal(
        base_metrics['cpu_base'], 5, periods
    ).clip(0, 100)
    memory = np.random.normal(
        base_metrics['mem_base'], 3, periods
    ).clip(0, 100)
    disk   = np.cumsum(
        np.random.normal(0.01, 0.005, periods)
    ) + base_metrics['disk_base']
    disk   = disk.clip(0, 100)
    requests = np.random.normal(
        base_metrics['req_base'], 100, periods
    ).clip(0)
    error_rate = np.random.normal(0.5, 0.2, periods).clip(0, 100)
    latency_ms = np.random.normal(150, 20, periods).clip(10)

    # Inject incident windows
    for incident in INCIDENT_WINDOWS:
        if incident['service'] != service_name:
            continue

        start_idx = int(incident['start_offset_hours'] * 12)
        end_idx   = start_idx + int(incident['duration_hours'] * 12)

        if incident['type'] == 'memory_spike':
            memory[start_idx:end_idx] = np.random.normal(
                92, 2, end_idx - start_idx
            ).clip(88, 100)
            error_rate[start_idx:end_idx] += 15

        elif incident['type'] == 'disk_full':
            disk[start_idx:end_idx] = np.random.normal(
                97, 1, end_idx - start_idx
            ).clip(95, 100)

        elif incident['type'] == 'cpu_spike':
            cpu[start_idx:end_idx] = np.random.normal(
                93, 2, end_idx - start_idx
            ).clip(88, 100)
            latency_ms[start_idx:end_idx] *= 3

        elif incident['type'] == 'memory_leak':
            memory[start_idx:end_idx] = np.linspace(
                base_metrics['mem_base'],
                95,
                end_idx - start_idx
            )

    df = pd.DataFrame({
        'timestamp'         : timestamps,
        'service'           : service_name,
        'cpu_percent'       : cpu.round(2),
        'memory_percent'    : memory.round(2),
        'disk_percent'      : disk.round(2),
        'requests_per_min'  : requests.round(0).astype(int),
        'error_rate_percent': error_rate.round(3),
        'latency_p95_ms'    : latency_ms.round(1),
    })

    return df


def main():
    print("FinTechFlow Metrics Generator")
    all_dfs = []

    for service, base in SERVICES.items():
        print(f"Generating metrics for {service}...")
        df = generate_service_metrics(service, base, days=7)

        # Save per service
        output = RAW_TABULAR / f"{service.replace('-', '_')}_metrics.csv"
        df.to_csv(output, index=False)
        all_dfs.append(df)
        print(f"  Saved {len(df):,} rows to {output.name}")

    # Save incident annotation
    annotations_path = RAW_TABULAR / "incident_annotations.json"
    with open(annotations_path, 'w') as f:
        json.dump(INCIDENT_WINDOWS, f, indent=2)

    print(f"\nAll metrics saved to {RAW_TABULAR}")
    print(f"Services: {list(SERVICES.keys())}")
    print(f"Incident windows annotated: {len(INCIDENT_WINDOWS)}")


if __name__ == "__main__":
    main()