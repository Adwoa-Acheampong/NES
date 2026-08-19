import os
from typing import List, Dict, Any
from nes.memory.vector_store import VectorStore
from nes.memory.embeddings import EmbeddingModel

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Simple character-based text chunker."""
    if not text:
        return []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

class DocumentIngester:
    def __init__(self, vector_store: VectorStore, embedding_model: EmbeddingModel):
        self.vector_store = vector_store
        self.embedding_model = embedding_model

    def ingest_text(self, text: str, metadata: Dict[str, Any] = None):
        """Ingests a raw string of text into the vector store."""
        if metadata is None:
            metadata = {}
            
        chunks = chunk_text(text)
        if not chunks:
            return
            
        # Add chunk index to metadata
        metadatas = [{"chunk": i, **metadata} for i in range(len(chunks))]
        
        # Get embeddings
        embeddings = self.embedding_model.embed_documents(chunks)
        
        # Store in vector store
        self.vector_store.add_documents(texts=chunks, metadatas=metadatas, embeddings=embeddings)
        print(f"Ingested {len(chunks)} chunks into vector store.")

    def ingest_file(self, file_path: str, metadata: Dict[str, Any] = None):
        """Ingests a text file from disk."""
        if metadata is None:
            metadata = {}
            
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        metadata["source"] = file_path
        self.ingest_text(content, metadata)
        
    def ingest_directory(self, directory_path: str, extensions: List[str] = ['.txt', '.md', '.py']):
        """Recursively ingests all supported files in a directory."""
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")
            
        count = 0
        for root, _, files in os.walk(directory_path):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    try:
                        self.ingest_file(file_path)
                        count += 1
                    except Exception as e:
                        print(f"Failed to ingest {file_path}: {e}")
                        
        print(f"Ingested {count} files from directory.")
