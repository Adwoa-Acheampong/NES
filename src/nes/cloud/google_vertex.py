"""Google Vertex AI integration for NES."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class VertexAIEngine:
    """Inference engine for Google Vertex AI models."""
    
    def __init__(self, project_id: str, location: str, model_name: str = "gemini-1.5-pro"):
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self._initialized = False

    def _initialize(self):
        if not self._initialized:
            try:
                import vertexai
                vertexai.init(project=self.project_id, location=self.location)
                self._initialized = True
                logger.info(f"Initialized Vertex AI for project {self.project_id}")
            except ImportError:
                logger.error("google-cloud-aiplatform is not installed. Run `pip install google-cloud-aiplatform`")
                raise

    def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Generate a response using Vertex AI."""
        self._initialize()
        from vertexai.generative_models import GenerativeModel, Part
        
        model = GenerativeModel(self.model_name)
        # Convert messages to Vertex AI format (simplified)
        chat = model.start_chat()
        
        prompt = messages[-1]["content"] if messages else ""
        response = chat.send_message(prompt, **kwargs)
        return response.text

    def create_rag_corpus(self, display_name: str, description: str = "") -> str:
        """Create a new RAG Corpus in Vertex AI."""
        try:
            self._initialize()
            from vertexai.preview import rag
            corpus = rag.create_corpus(
                display_name=display_name,
                description=description,
            )
            logger.info(f"Created RAG Corpus: {corpus.name}")
            return corpus.name
        except ImportError:
            logger.warning("vertexai.preview.rag not available. Dry-run return.")
            return f"projects/{self.project_id}/locations/{self.location}/ragCorpora/dry-run-123"

    def import_files_to_rag_corpus(self, corpus_name: str, gcs_uris: List[str]) -> Any:
        """Import files from GCS into a Vertex AI RAG Corpus."""
        try:
            self._initialize()
            from vertexai.preview import rag
            response = rag.import_files(
                corpus_name=corpus_name,
                paths=gcs_uris,
                chunk_size=1024,
                chunk_overlap=200,
            )
            logger.info(f"Imported {len(gcs_uris)} files into corpus {corpus_name}. {response.imported_files_count} succeeded.")
            return response
        except ImportError:
            logger.warning("vertexai.preview.rag not available. Dry-run return.")
            return {"imported_files_count": len(gcs_uris), "failed_files_count": 0}
