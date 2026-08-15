import json, pandas as pd
from pathlib import Path

PROJECT_ROOT = Path("C:/Users/sudha/techops-intelligence")
real_incidents_path = PROJECT_ROOT / "data/raw/text/incidents/real_incidents"

# Load all incidents
all_incidents = []
for json_file in sorted(real_incidents_path.glob("*.json")):
    with open(json_file, 'r') as f:
        data = json.load(f)
    for record in data:
        record['year'] = json_file.stem
    all_incidents.extend(data)

df_real = pd.DataFrame(all_incidents)

# ── Step 1: Filter Out Maintenance ───────
severity_map = {
    'critical': 'P1', 'major': 'P1',
    'medium': 'P2', 'minor': 'P3', 'low': 'P4'
}
df_real_filtered = df_real[
    df_real['severity'].str.lower().isin(severity_map.keys())
].copy()

print("=== After Filtering Maintenance ===")
print("Count :", len(df_real_filtered))

# ── Step 2: Map Severity → Priority ──────
df_real_filtered['priority_clean'] = df_real_filtered['severity'].str.lower().map(severity_map)

print("\nPriority distribution:")
print(df_real_filtered['priority_clean'].value_counts())

# ── Step 3: Map Category → System ────────
category_map = {
    'comms': 'network', 'cdn': 'network',
    'observability': 'monitoring', 'devtools': 'application',
    'paas': 'infrastructure', 'data': 'database',
    'cloud': 'infrastructure', 'ai': 'application'
}
df_real_filtered['category_clean'] = df_real_filtered['category'].map(category_map).fillna('application')

# ── Step 4: Rich Text for RAG ────────────
df_real_filtered['incident_text'] = (
    df_real_filtered['title'].fillna('Unknown') +
    ". Provider: " + df_real_filtered['provider_name'].fillna('Unknown') +
    ". Category: " + df_real_filtered['category_clean'] +
    ". Severity: " + df_real_filtered['severity'] +
    ". Duration: " + df_real_filtered['duration_minutes'].fillna(0).astype(int).astype(str) + " minutes."
)

# ── Step 5: MTTR Analysis ────────────────
p1_mttr = df_real_filtered[df_real_filtered['priority_clean'] == 'P1']['duration_minutes'].median()
print("\n=== MTTR Resume Metric ===")
print(f"P1 MTTR median : {p1_mttr:.0f} mins")

# ── Step 6: Keep Useful Columns ──────────
final_cols = [
    'incident_id','title','provider_name','category','category_clean',
    'severity','priority_clean','status','duration_minutes',
    'created_at','resolved_at','year','incident_text'
]
df_real_final = df_real_filtered[final_cols]

# ── Step 7: Save ─────────────────────────
df_real_final.to_csv(PROJECT_ROOT / "data/processed/real_incidents_clean.csv", index=False)
print("\n✓ Saved → data/processed/real_incidents_clean.csv")
print(f"Rows    : {len(df_real_final):,}")
print(f"Columns : {df_real_final.shape[1]}")
