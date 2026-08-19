import os
import tempfile
from io import BytesIO
from pathlib import Path

from azure.storage.blob import BlobServiceClient
from langchain_community.document_loaders import PyPDFDirectoryLoader, PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

DATA_DIR = Path(__file__).resolve().parent / "data"
BLOB_CONTAINER_URL = os.getenv("BLOB_CONTAINER_URL")
INDEX_CONTAINER_NAME = os.getenv("INDEX_CONTAINER_NAME")


class SimpleRAGEngine:
    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir) if data_dir is not None else DATA_DIR
        self.vector_store = None
        self.embeddings = None
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        self.initialize_store()

    def _load_embeddings(self):
        """Load lightweight embedding model."""
        if not self.embeddings:
            self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    def _load_documents_from_blob(self) -> list:
        """Load all PDFs from Azure Blob Storage."""
        print("Chargement des PDF depuis Azure Blob Storage...")
        try:
            blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONTAINER_URL)
            container_client = blob_service_client.get_container_client(container="documents")
            documents = []

            for blob in container_client.list_blobs():
                if blob.name.endswith(".pdf"):
                    print(f"  Téléchargement: {blob.name}")
                    blob_client = container_client.get_blob_client(blob.name)
                    blob_data = blob_client.download_blob().readall()

                    tmp_path = None
                    try:
                        # PyPDFLoader a besoin d'un vrai chemin de fichier, pas d'un BytesIO
                        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                            tmp_file.write(blob_data)
                            tmp_path = tmp_file.name

                        pdf_loader = PyPDFLoader(tmp_path)
                        docs = pdf_loader.load()
                        documents.extend(docs)
                    except Exception as e:
                        print(f"  Erreur lors du chargement de {blob.name}: {e}")
                    finally:
                        if tmp_path and os.path.exists(tmp_path):
                            os.unlink(tmp_path)

            return documents
        except Exception as exc:
            print(f"Warning: Impossible de charger depuis Blob Storage: {exc}")
            return []

    def _load_documents_from_local(self) -> list:
        """Load all PDFs from local data directory."""
        print(f"Chargement des PDF depuis {self.data_dir}...")
        if not self.data_dir.exists() or not any(self.data_dir.glob("*.pdf")):
            print("Attention : Aucun PDF trouvé localement. Indexation ignorée.")
            return []

        try:
            loader = PyPDFDirectoryLoader(str(self.data_dir))
            documents = loader.load()
            return documents
        except Exception as exc:
            print(f"Warning: impossible de charger les PDF locaux: {exc}")
            return []

    def _load_prebuilt_index_from_blob(self):
        """Download and load a prebuilt FAISS index (index.faiss + index.pkl) from Blob Storage."""
        print(f"Chargement de l'index pre-construit depuis le container '{INDEX_CONTAINER_NAME}'...")
        try:
            blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONTAINER_URL)
            container_client = blob_service_client.get_container_client(container=INDEX_CONTAINER_NAME)

            with tempfile.TemporaryDirectory() as tmp_dir:
                for blob_name in ["index.faiss", "index.pkl"]:
                    blob_client = container_client.get_blob_client(blob_name)
                    data = blob_client.download_blob().readall()
                    local_path = os.path.join(tmp_dir, blob_name)
                    with open(local_path, "wb") as f:
                        f.write(data)

                self.vector_store = FAISS.load_local(
                    tmp_dir, self.embeddings, allow_dangerous_deserialization=True
                )
            print("Index pre-construit charge avec succes.")
            return True
        except Exception as exc:
            print(f"Warning: impossible de charger l'index pre-construit: {exc}")
            return False

    def initialize_store(self):
        """Initialize vector store from a prebuilt index, Blob Storage, or local files."""
        try:
            self._load_embeddings()

            if INDEX_CONTAINER_NAME:
                if self._load_prebuilt_index_from_blob():
                    return

            if BLOB_CONTAINER_URL:
                documents = self._load_documents_from_blob()
            else:
                documents = self._load_documents_from_local()

            if not documents:
                print("Aucun document à indexer.")
                self.vector_store = None
                return

            chunks = self.text_splitter.split_documents(documents)
            print(f"Indexation de {len(chunks)} chunks en cours...")
            self.vector_store = FAISS.from_documents(chunks, self.embeddings)
            print("Base vectorielle prête !")
        except Exception as exc:
            print(f"Warning: impossible d'initialiser le moteur RAG: {exc}")
            self.vector_store = None

    def add_documents_from_bytes(self, pdf_bytes: bytes, source_name: str = "uploaded") -> str:
        """Add documents from a PDF byte stream to the existing vector store (ephemeral)."""
        tmp_path = None
        try:
            self._load_embeddings()

            # PyPDFLoader a besoin d'un vrai chemin de fichier, pas d'un BytesIO
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file.write(pdf_bytes)
                tmp_path = tmp_file.name

            pdf_loader = PyPDFLoader(tmp_path)
            documents = pdf_loader.load()

            if not documents:
                return "Erreur: Aucun contenu n'a pu être extrait du PDF."

            # Mark documents with source
            for doc in documents:
                doc.metadata["source"] = source_name

            chunks = self.text_splitter.split_documents(documents)
            print(f"Ajout de {len(chunks)} chunks depuis {source_name}...")

            # Add to existing store or create new one
            if self.vector_store:
                self.vector_store.add_documents(chunks)
            else:
                self.vector_store = FAISS.from_documents(chunks, self.embeddings)

            return f"Succès: {len(chunks)} chunks ajoutés à l'index."
        except Exception as exc:
            return f"Erreur lors du traitement du PDF: {str(exc)}"
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def ingest(self) -> str:
        """Refresh the in-memory index from Blob Storage or local files."""
        self.initialize_store()
        if self.vector_store:
            return "Réindexation réussie."
        else:
            return "Réindexation échouée: aucun document disponible."

    def search(self, query: str, k: int = 3) -> str:
        """Return the most relevant context chunks without generating final prose."""
        if not self.vector_store:
            return "Erreur : La base de connaissances est vide. Ajoutez des PDF via /upload ou configurez BLOB_CONTAINER_URL."

        results = self.vector_store.similarity_search(query, k=k)
        context = "\n\n".join(
            [f"Extrait {i + 1}:\n{doc.page_content}" for i, doc in enumerate(results)]
        )
        return context


rag_engine = SimpleRAGEngine()