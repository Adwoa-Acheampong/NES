import os
from nes.sdk import NES

# Script to test a fine-tuned RAG model hosted on Vertex AI / Alibaba PAI
# After fine-tuning on the JSONL from step 1, you can deploy your open weights model
# using an OpenAI-compatible interface like vLLM or PAI-EAS.

def test_cloud_model():
    # Set the base URL to your Cloud endpoint.
    # Google Cloud example (vLLM on GKE/GCE): http://<external-ip>:8000/v1
    # Alibaba PAI example: http://<pai-eas-endpoint>.pai-eas.aliyuncs.com/v1
    os.environ["OPENAI_BASE_URL"] = "http://localhost:8000/v1" # Replace with your cloud endpoint
    os.environ["OPENAI_API_KEY"] = "YOUR_CLOUD_API_KEY"
    
    print(f"Connecting to Cloud RAG Endpoint at {os.environ.get('OPENAI_BASE_URL')}...")
    
    with NES() as agent:
        # We use the CloudEngine adapter (which we updated to support context_injection)
        # by routing to the 'cloud' engine.
        print("Sending query with context_injection=True to the fine-tuned model...")
        
        # In a real environment, NES automatically uses the configured memory backend
        # to inject documents. Because we modified `cloud.py` earlier, it will now
        # intercept these context documents and format them perfectly into the system prompt!
        
        response = agent.ask(
            "How do I restart the mining pool?",
            # The context_injection=True flag invokes our newly written logic in cloud.py!
            context_injection=True
        )
        
        print("\n=== RESPONSE FROM CLOUD MODEL ===")
        print(response)
        print("=================================")

if __name__ == "__main__":
    test_cloud_model()
