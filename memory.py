import chromadb

# Set up persistent Chroma client saved to ./chroma_db folder
client = chromadb.PersistentClient(path="./chroma_db")

# Get or create the "incidents" collection
collection = client.get_or_create_collection("incidents")

def embed_incident(
    id: str,
    title: str,
    root_cause: str,
    fix: str,
    postmortem: str
) -> None:
    """
    Combines all fields into one text string and stores it in Chroma
    with the incident id as the document id.
    """
    combined_text = (
        f"Title: {title}\n"
        f"Root Cause: {root_cause}\n"
        f"Fix: {fix}\n"
        f"Postmortem: {postmortem}"
    )
    
    collection.upsert(
        documents=[combined_text],
        ids=[str(id)]
    )

def search_similar_incidents(query: str, n_results: int = 3) -> list[str]:
    """
    Takes a query string (e.g. the PR diff) and returns the top
    n_results most similar incident texts.
    """
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    if results and "documents" in results and results["documents"]:
        # Chroma returns a list of lists of documents. Return the first list.
        return results["documents"][0]
    return []


def delete_incident(id: str) -> None:
    """
    Deletes an incident embedding from Chroma vector DB by ID.
    """
    collection.delete(ids=[str(id)])

