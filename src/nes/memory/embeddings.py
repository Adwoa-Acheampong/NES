import abc
from typing import List
import json
import urllib.request
import urllib.error

class EmbeddingModel(abc.ABC):
    @abc.abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        pass
        
    @abc.abstractmethod
    def embed_query(self, text: str) -> List[float]:
        pass

class OllamaEmbeddingModel(EmbeddingModel):
    def __init__(self, model_name: str = "nomic-embed-text", host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.host = host
        
    def _get_embedding(self, text: str) -> List[float]:
        url = f"{self.host}/api/embeddings"
        data = json.dumps({"model": self.model_name, "prompt": text}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('embedding', [])
        except urllib.error.URLError as e:
            print(f"Error connecting to Ollama for embeddings: {e}")
            return []

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._get_embedding(text) for text in texts]
        
    def embed_query(self, text: str) -> List[float]:
        return self._get_embedding(text)

class MockEmbeddingModel(EmbeddingModel):
    """A mock embedding model for testing that just returns random vectors."""
    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        import random
        self.random = random
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[self.random.uniform(-1, 1) for _ in range(self.dimension)] for _ in texts]
        
    def embed_query(self, text: str) -> List[float]:
        return [self.random.uniform(-1, 1) for _ in range(self.dimension)]
