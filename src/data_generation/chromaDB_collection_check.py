import chromadb
from pathlib import Path

PROJECT_ROOT = Path("C:/Users/sudha/techops-intelligence")
client = chromadb.PersistentClient(
    path=str(PROJECT_ROOT / "data/embeddings/chroma_db")
)

print("Current ChromaDB state:\n")
for col in client.list_collections():
    c     = client.get_collection(col.name)
    count = c.count()
    print(f"  {col.name:20} : {count:,} docs")

    # Show sample source metadata
    if count > 0:
        sample = c.get(limit=3, include=['metadatas'])
        sources = set(
            m.get('source', 'unknown')
            for m in sample['metadatas']
        )
        print(f"  {'':20}   sources: {sources}")