import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path("C:/Users/sudha/techops-intelligence")

df1 = pd.read_csv(PROJECT_ROOT / "data/processed/real_incidents_clean.csv")
df2 = pd.read_csv(PROJECT_ROOT / "data/processed/real_incidents_AI_clean.csv")

print(f"real_incidents_clean.csv    : {df1.shape}")
print(f"real_incidents_AI_clean.csv : {df2.shape}")
print(f"\nreal_incidents_clean columns    : {df1.columns.tolist()}")
print(f"\nreal_incidents_AI_clean columns : {df2.columns.tolist()}")