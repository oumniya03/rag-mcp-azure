"""
Script d'indexation hors ligne pour le dataset MedQuAD complet.

A executer localement (PAS dans le conteneur deploye) pour construire
un index FAISS a partir de medquad.csv en entier. Les fichiers d'index
generes seront ensuite uploades vers Azure Blob Storage, ou le service
en production les telechargera et les chargera directement au demarrage,
sans jamais recalculer les embeddings.

Usage:
    python scripts/build_index_offline.py
"""
import csv
import sys
import time
from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.docstore.document import Document

CSV_PATH = Path("medquad.csv")
OUTPUT_DIR = Path("medquad_index")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def load_documents(csv_path: Path) -> list[Document]:
    csv.field_size_limit(sys.maxsize)
    documents = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            question = (row.get("question") or "").strip()
            answer = (row.get("answer") or "").strip()
            focus_area = (row.get("focus_area") or "").strip()
            source = (row.get("source") or "").strip()

            if not question or not answer:
                continue

            content = f"Question: {question}\nAnswer: {answer}"
            documents.append(
                Document(
                    page_content=content,
                    metadata={"focus_area": focus_area, "source": source},
                )
            )
    return documents


def main():
    if not CSV_PATH.exists():
        print(f"Fichier introuvable : {CSV_PATH.resolve()}")
        sys.exit(1)

    print(f"Lecture de {CSV_PATH} ...")
    documents = load_documents(CSV_PATH)
    print(f"{len(documents)} paires question/reponse chargees.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    print("Decoupage en chunks ...")
    chunks = splitter.split_documents(documents)
    print(f"{len(chunks)} chunks generes.")

    print("Chargement du modele d'embeddings (all-MiniLM-L6-v2) ...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    print("Calcul des embeddings et construction de l'index FAISS ...")
    print("Cette etape peut prendre plusieurs dizaines de minutes. Patience.")
    start = time.time()
    vector_store = FAISS.from_documents(chunks, embeddings)
    elapsed = time.time() - start
    print(f"Index construit en {elapsed / 60:.1f} minutes.")

    OUTPUT_DIR.mkdir(exist_ok=True)
    vector_store.save_local(str(OUTPUT_DIR))
    print(f"Index sauvegarde dans {OUTPUT_DIR.resolve()}")
    print("Fichiers generes : index.faiss, index.pkl")


if __name__ == "__main__":
    main()