# ─────────────────────────────────────────
# DAN LUU POSTMORTEMS — FULL PROCESSING
# Both summary AND content are useful
# ─────────────────────────────────────────
import json
from pathlib import Path

PROJECT_ROOT = Path("C:/Users/sudha/techops-intelligence")
danluu_path  = PROJECT_ROOT / "data/raw/postmortems_danluu/postmortems_danluu.jsonl"

postmortems_clean = []

with open(danluu_path, 'r', errors='ignore') as f:
    for line in f:
        entry   = json.loads(line)
        summary = entry.get('summary', '')
        content = entry.get('content', '')

        # Skip entries with no useful content
        if content == 'Redirecting...' and len(summary) < 80:
            continue

        # Combine summary + content for richer RAG context
        full_text = ""
        if summary:
            full_text += f"Summary: {summary}\n\n"
        if content and content != 'Redirecting...':
            full_text += f"Details: {content[:2000]}"
            # cap at 2000 chars per entry
            # prevents single entry dominating retrieval

        if len(full_text.strip()) < 50:
            continue

        postmortems_clean.append({
            'id'        : entry.get('id'),
            'source'    : entry.get('source', ''),
            'url'       : entry.get('url', ''),
            'summary'   : summary,
            'full_text' : full_text.strip(),
            'has_content': content != 'Redirecting...'
        })

print(f"=== Dan Luu Postmortems — Cleaned ===")
print(f"Total raw entries  : 234")
print(f"Usable entries     : {len(postmortems_clean)}")
print(f"With full content  : {sum(1 for p in postmortems_clean if p['has_content'])}")
print(f"Summary only       : {sum(1 for p in postmortems_clean if not p['has_content'])}")

# Company breakdown
from collections import Counter
companies = Counter(p['source'] for p in postmortems_clean)
print(f"\nTop 15 companies:")
for company, count in companies.most_common(15):
    print(f"  {company:30} : {count}")

# Text length stats
import numpy as np
lengths = [len(p['full_text']) for p in postmortems_clean]
print(f"\nText length stats:")
print(f"  Mean   : {np.mean(lengths):.0f} chars")
print(f"  Median : {np.median(lengths):.0f} chars")
print(f"  Max    : {np.max(lengths):.0f} chars")
print(f"  Min    : {np.min(lengths):.0f} chars")

# Sample good entry
print(f"\nSample entry (full_text preview):")
sample = [p for p in postmortems_clean if p['has_content']][2]
print(f"Source: {sample['source']}")
print(f"Text preview:\n{sample['full_text'][:400]}")

# Save
output_path = PROJECT_ROOT / "data/processed/danluu_postmortems.json"
with open(output_path, 'w') as f:
    json.dump(postmortems_clean, f, indent=2)

print(f"\n✓ Saved {len(postmortems_clean)} postmortems")
print(f"  → data/processed/danluu_postmortems.json")