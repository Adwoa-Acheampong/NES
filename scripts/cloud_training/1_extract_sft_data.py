import json
from pathlib import Path
from nes.sdk import NES

# Script to extract RAG query data from NES and format as OpenAI ChatML JSONL
# This can be uploaded to Google Vertex AI or Alibaba PAI for LoRA fine-tuning.

def export_training_data(output_file: str, min_score: float = 0.8):
    print("Initializing NES to read memory and context logs...")
    
    with NES() as agent:
        # NES MemoryHandle allows searching semantic history.
        # We simulate querying the top N interactions to build training pairs.
        
        # Example: Fetch highest quality stored interactions that used context_injection
        print("Querying memory backend for successful RAG completions...")
        try:
            results = agent.memory.search("successful rag resolutions", top_k=1000)
        except Exception as e:
            print("No memory backend active or empty database. Generating mock training data for demonstration.")
            results = [
                {
                    "query": "How do I restart the mining pool?",
                    "context": "To restart the mining pool, execute `systemctl restart nes-pool`.",
                    "response": "You can restart the mining pool by running the command `systemctl restart nes-pool`."
                }
            ]
        
        valid_pairs = []
        for r in results:
            # Format as OpenAI ChatML
            pair = {
                "messages": [
                    {
                        "role": "system", 
                        "content": f"You are NES. Use this context to answer:\n{r.get('context', '')}"
                    },
                    {
                        "role": "user",
                        "content": r.get('query', '')
                    },
                    {
                        "role": "assistant",
                        "content": r.get('response', '')
                    }
                ]
            }
            valid_pairs.append(pair)
            
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out_path, "w", encoding="utf-8") as f:
            for p in valid_pairs:
                f.write(json.dumps(p) + "\n")
                
        print(f"Exported {len(valid_pairs)} SFT examples to {out_path.absolute()}")
        print("You can now upload this JSONL file to Vertex AI or Alibaba PAI for tuning!")

if __name__ == "__main__":
    export_training_data("scripts/cloud_training/sft_dataset.jsonl")
