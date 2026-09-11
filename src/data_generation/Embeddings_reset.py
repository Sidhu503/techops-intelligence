import chromadb
from pathlib import Path

PROJECT_ROOT = Path("C:/Users/sudha/techops-intelligence")
client = chromadb.PersistentClient(
    path=str(PROJECT_ROOT / "data/embeddings/chroma_db")
)

# Collections to wipe and recreate with FTF data
to_reset = ['incidents', 'postmortems', 'playbooks', 'logs']

for name in to_reset:
    try:
        client.delete_collection(name)
        client.create_collection(
            name     = name,
            metadata = {"hnsw:space": "cosine"}
        )
        print(f"Reset: {name}")
    except Exception as e:
        print(f"Error on {name}: {e}")

# Delete visuals entirely
try:
    client.delete_collection("visuals")
    print("Deleted: visuals")
except Exception:
    print("visuals not found")

print("\nChromaDB after reset:")
for col in client.list_collections():
    c = client.get_collection(col.name)
    print(f"  {col.name:20} : {c.count():,} docs")