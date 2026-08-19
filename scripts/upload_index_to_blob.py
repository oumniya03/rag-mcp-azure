"""
Upload FAISS index files to Azure Blob Storage.
Usage: BLOB_CONNECTION_STRING="your_connection_string" python scripts/upload_index_to_blob.py
"""
import os
import sys
from pathlib import Path
from azure.storage.blob import BlobServiceClient

INDEX_DIR = Path("medquad_index")
CONTAINER_NAME = "medquad-index"
FILES = ["index.faiss", "index.pkl"]

def main():
    connection_string = os.getenv("BLOB_CONNECTION_STRING")
    if not connection_string:
        print("ERREUR: Variable d'environnement BLOB_CONNECTION_STRING manquante")
        print("Usage: BLOB_CONNECTION_STRING=\"your_connection_string\" python scripts/upload_index_to_blob.py")
        sys.exit(1)

    print(f"Connexion à Azure Blob Storage...")
    # Increase timeout to 10 minutes for large files
    blob_service_client = BlobServiceClient.from_connection_string(
        connection_string,
        connection_timeout=600,  # 10 minutes
        read_timeout=600
    )
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)

    # Create container if not exists
    try:
        container_client.create_container()
        print(f"Container '{CONTAINER_NAME}' créé.")
    except Exception:
        print(f"Container '{CONTAINER_NAME}' existe déjà.")

    for filename in FILES:
        local_path = INDEX_DIR / filename
        if not local_path.exists():
            print(f"ERREUR: Fichier introuvable: {local_path}")
            sys.exit(1)

        file_size_mb = local_path.stat().st_size / 1024 / 1024
        print(f"Upload de {filename} ({file_size_mb:.1f} MB)...")
        blob_client = container_client.get_blob_client(filename)
        with open(local_path, "rb") as f:
            # Simple upload with overwrite - SDK handles chunking automatically
            blob_client.upload_blob(f, overwrite=True)
        print(f"  ✓ {filename} uploadé avec succès.")

    print("\n✅ Index uploadé avec succès dans le container 'medquad-index'")
    print("Le service de production le chargera au prochain redémarrage.")

if __name__ == "__main__":
    main()