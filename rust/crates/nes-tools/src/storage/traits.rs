//! MemoryBackend trait for all storage backends.

use nes_core::{NESError, RetrievalResult};
use serde_json::Value;

pub trait MemoryBackend: Send + Sync {
    fn backend_id(&self) -> &str;
    fn store(
        &self,
        content: &str,
        source: &str,
        metadata: Option<&Value>,
    ) -> Result<String, NESError>;
    fn retrieve(
        &self,
        query: &str,
        top_k: usize,
    ) -> Result<Vec<RetrievalResult>, NESError>;
    fn delete(&self, doc_id: &str) -> Result<bool, NESError>;
    fn clear(&self) -> Result<(), NESError>;
    fn count(&self) -> Result<usize, NESError>;
}
