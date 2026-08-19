"""RAG Uploader for bundling and uploading data to Cloud."""

import os
import zipfile
import json
import logging
from typing import List, Dict, Union, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class RAGUploader:
    """Utility to bundle training/RAG data and upload to cloud storage."""
    
    def __init__(self, work_dir: str = "/tmp/rag_workspace"):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def bundle_documents(self, docs_dir: str, output_name: str = "rag_bundle.zip") -> str:
        """Bundle a directory of documents into a ZIP file."""
        output_path = self.work_dir / output_name
        logger.info(f"Bundling documents from {docs_dir} into {output_path}")
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(docs_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, docs_dir)
                    zipf.write(file_path, arcname)
                    
        return str(output_path)

    def bundle_jsonl(self, data: List[Dict], output_name: str = "rag_data.jsonl") -> str:
        """Bundle a list of dictionaries into a JSONL file."""
        output_path = self.work_dir / output_name
        logger.info(f"Bundling {len(data)} items into {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
                
        return str(output_path)

    def upload_to_gcs(self, file_path: str, bucket_name: str, destination_blob_name: str) -> str:
        """Upload a file to Google Cloud Storage."""
        logger.info(f"Uploading {file_path} to GCS bucket {bucket_name} as {destination_blob_name}")
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_filename(file_path)
            gcs_uri = f"gs://{bucket_name}/{destination_blob_name}"
            logger.info(f"Successfully uploaded to {gcs_uri}")
            return gcs_uri
        except ImportError:
            logger.warning("google-cloud-storage is not installed. Performing dry-run.")
            return f"gs://{bucket_name}/{destination_blob_name}"
        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            raise

    def upload_to_oss(self, file_path: str, bucket_name: str, endpoint: str, access_key_id: str, access_key_secret: str, destination_name: str) -> str:
        """Upload a file to Alibaba Cloud OSS."""
        logger.info(f"Uploading {file_path} to OSS bucket {bucket_name} as {destination_name}")
        try:
            import oss2
            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, endpoint, bucket_name)
            bucket.put_object_from_file(destination_name, file_path)
            oss_uri = f"oss://{bucket_name}/{destination_name}"
            logger.info(f"Successfully uploaded to {oss_uri}")
            return oss_uri
        except ImportError:
            logger.warning("oss2 is not installed. Performing dry-run.")
            return f"oss://{bucket_name}/{destination_name}"
        except Exception as e:
            logger.error(f"OSS upload failed: {e}")
            raise
