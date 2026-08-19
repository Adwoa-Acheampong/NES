import abc
from typing import List, Dict, Any, Tuple
import math

class VectorStore(abc.ABC):
    @abc.abstractmethod
    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]] = None, embeddings: List[List[float]] = None):
        pass
        
    @abc.abstractmethod
    def similarity_search(self, query_embedding: List[float], k: int = 4) -> List[Tuple[str, Dict[str, Any], float]]:
        """Returns top k documents with their metadata and similarity score."""
        pass

class InMemoryVectorStore(VectorStore):
    """A simple in-memory vector store using cosine similarity. Good for local testing without dependencies."""
    def __init__(self):
        self.texts = []
        self.metadatas = []
        self.embeddings = []
        
    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]] = None, embeddings: List[List[float]] = None):
        if not embeddings or len(texts) != len(embeddings):
            raise ValueError("Embeddings must be provided and match the number of texts.")
            
        if metadatas is None:
            metadatas = [{} for _ in texts]
            
        self.texts.extend(texts)
        self.metadatas.extend(metadatas)
        self.embeddings.extend(embeddings)
        
    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
            
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
        
    def similarity_search(self, query_embedding: List[float], k: int = 4) -> List[Tuple[str, Dict[str, Any], float]]:
        if not self.embeddings:
            return []
            
        results = []
        for idx, emb in enumerate(self.embeddings):
            score = self._cosine_similarity(query_embedding, emb)
            results.append((score, idx))
            
        # Sort by score descending
        results.sort(reverse=True, key=lambda x: x[0])
        
        # Take top k
        top_k = results[:k]
        
        return [(self.texts[idx], self.metadatas[idx], score) for score, idx in top_k]
