"""Pipeline for RAG training data preparation and upload."""

import os
import logging
import argparse
from typing import Optional
from pathlib import Path

from nes.cloud.rag_uploader import RAGUploader
from nes.cloud.google_vertex import VertexAIEngine
from nes.cloud.alibaba_pai import AlibabaPAIEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class RAGPipeline:
    """Orchestrates data bundling and cloud RAG corpus updating."""

    def __init__(self, provider: str = "google", work_dir: str = "/tmp/rag_workspace"):
        self.provider = provider.lower()
        self.uploader = RAGUploader(work_dir=work_dir)
        
    def process(self, source_dir: str, bucket_name: str, corpus_id: Optional[str] = None):
        """Bundle data from source_dir and upload to the chosen provider's RAG storage."""
        if not os.path.exists(source_dir):
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

        # 1. Bundle the data
        bundle_path = self.uploader.bundle_documents(source_dir, output_name="rag_bundle.zip")
        
        # 2. Upload to Cloud Storage and import to Vector Search
        if self.provider == "google":
            self._process_google(bundle_path, bucket_name, corpus_id)
        elif self.provider == "alibaba":
            self._process_alibaba(bundle_path, bucket_name, corpus_id)
        else:
            raise ValueError(f"Unsupported cloud provider: {self.provider}")

    def _process_google(self, bundle_path: str, bucket_name: str, corpus_id: Optional[str]):
        """Upload to GCS and import to Vertex AI RAG Corpus."""
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "test-project")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        
        engine = VertexAIEngine(project_id=project_id, location=location)
        
        # Upload to GCS
        file_name = os.path.basename(bundle_path)
        gcs_uri = self.uploader.upload_to_gcs(bundle_path, bucket_name, f"rag_data/{file_name}")
        
        # Setup RAG Corpus
        if not corpus_id:
            logger.info("No corpus_id provided. Creating a new Vertex AI RAG Corpus...")
            corpus_id = engine.create_rag_corpus(display_name="nes-training-rag")
            
        # Import to Corpus
        logger.info(f"Importing {gcs_uri} into Vertex AI Corpus {corpus_id}...")
        result = engine.import_files_to_rag_corpus(corpus_id, [gcs_uri])
        logger.info(f"Pipeline complete. Vertex AI Import Result: {result}")

    def _process_alibaba(self, bundle_path: str, bucket_name: str, kb_id: Optional[str]):
        """Upload to OSS and import to Alibaba PAI Knowledge Base."""
        endpoint = os.environ.get("ALIBABA_OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com")
        ak_id = os.environ.get("ALIBABA_ACCESS_KEY_ID", "test-ak")
        ak_secret = os.environ.get("ALIBABA_ACCESS_KEY_SECRET", "test-secret")
        pai_endpoint = os.environ.get("ALIBABA_PAI_ENDPOINT", "https://pai.aliyuncs.com")
        pai_token = os.environ.get("ALIBABA_PAI_TOKEN", "test-token")
        
        engine = AlibabaPAIEngine(endpoint=pai_endpoint, token=pai_token)
        
        # Upload to OSS
        file_name = os.path.basename(bundle_path)
        oss_uri = self.uploader.upload_to_oss(
            bundle_path, 
            bucket_name, 
            endpoint=endpoint,
            access_key_id=ak_id,
            access_key_secret=ak_secret,
            destination_name=f"rag_data/{file_name}"
        )
        
        if not kb_id:
            logger.warning("No knowledge base ID provided. Using default 'nes-kb-001'")
            kb_id = "nes-kb-001"
            
        # Import to KB
        logger.info(f"Importing {oss_uri} into PAI Knowledge Base {kb_id}...")
        result = engine.upload_to_knowledge_base(kb_id, [oss_uri])
        logger.info(f"Pipeline complete. Alibaba PAI Import Result: {result}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NES RAG Pipeline")
    parser.add_argument("--source", type=str, required=True, help="Directory containing RAG documents.")
    parser.add_argument("--provider", type=str, choices=["google", "alibaba"], default="google", help="Cloud provider to use.")
    parser.add_argument("--bucket", type=str, required=True, help="Target bucket (GCS or OSS).")
    parser.add_argument("--corpus-id", type=str, help="Existing Corpus ID / Knowledge Base ID.")
    
    args = parser.parse_args()
    
    pipeline = RAGPipeline(provider=args.provider)
    pipeline.process(source_dir=args.source, bucket_name=args.bucket, corpus_id=args.corpus_id)
