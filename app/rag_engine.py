import os
from pathlib import Path

from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

DATA_DIR = Path(__file__).resolve().parent / "data"


class SimpleRAGEngine:
    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir) if data_dir is not None else DATA_DIR
        self.vector_store = None
        self.embeddings = None
        self.initialize_store()

    def initialize_store(self):
        print(f"Chargement des PDF depuis {self.data_dir}...")
        if not self.data_dir.exists() or not any(self.data_dir.iterdir()):
            print("Attention : Aucun PDF trouvé dans app/data/. Indexation ignorée.")
            return

        try:
            # lightweight embedding model selected to fit in 8 GB RAM local environment
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

            loader = PyPDFDirectoryLoader(str(self.data_dir))
            documents = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            chunks = text_splitter.split_documents(documents)

            print(f"Indexation de {len(chunks)} chunks en cours...")
            self.vector_store = FAISS.from_documents(chunks, self.embeddings)
            print("Base vectorielle prête !")
        except Exception as exc:
            print(f"Warning: impossible d'initialiser le moteur RAG: {exc}")
            self.vector_store = None
            self.embeddings = None

    def ingest(self):
        """Refresh the in-memory index from the configured data folder."""
        self.initialize_store()

    def search(self, query: str, k: int = 3) -> str:
        """Return the most relevant context chunks without generating final prose."""
        if not self.vector_store:
            return "Erreur : La base de connaissances est vide. Ajoutez des PDF dans app/data/."

        results = self.vector_store.similarity_search(query, k=k)
        context = "\n\n".join(
            [f"Extrait {i + 1}:\n{doc.page_content}" for i, doc in enumerate(results)]
        )
        return context


rag_engine = SimpleRAGEngine()
