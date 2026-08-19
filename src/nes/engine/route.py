"""Routing engine with RAG support for NES."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class RouterEngine:
    """Routes requests to the appropriate agent and injects RAG context if applicable."""
    
    def __init__(self, retriever=None):
        """Initialize the router with an optional knowledge retriever."""
        self.retriever = retriever
        self.agent_registry = {}
        
    def register_agent(self, name: str, description: str, endpoint: Any):
        """Register an agent with its capabilities."""
        self.agent_registry[name] = {
            "description": description,
            "endpoint": endpoint
        }
        logger.info(f"Registered agent {name}")
        
    def route_request(self, user_query: str) -> str:
        """Determine which agent should handle the query using RAG support if available."""
        # Check if RAG retriever is available to inform routing
        if self.retriever:
            try:
                # Retrieve relevant routing documents (e.g., agent capabilities or related topics)
                routing_docs = self.retriever.retrieve(f"Routing request: {user_query}")
                if routing_docs:
                    combined_docs = " ".join(routing_docs).lower()
                    
                    # Evaluate each agent against the retrieved RAG context and the user query
                    best_agent = "default_agent"
                    best_score = -1
                    
                    for name, data in self.agent_registry.items():
                        score = 0
                        name_lower = name.lower()
                        desc_lower = data.get("description", "").lower()
                        
                        # Score based on direct query match
                        if name_lower in user_query.lower():
                            score += 5
                        if desc_lower and any(word in user_query.lower() for word in desc_lower.split() if len(word) > 4):
                            score += 2
                            
                        # Score based on RAG context match
                        if name_lower in combined_docs:
                            score += 3
                        if desc_lower and any(word in combined_docs for word in desc_lower.split() if len(word) > 4):
                            score += 1
                            
                        if score > best_score:
                            best_score = score
                            best_agent = name
                            
                    if best_score > 0:
                        logger.info(f"RAG routing selected agent: {best_agent} with score {best_score}")
                        return best_agent
            except Exception as e:
                logger.warning(f"RAG routing failed, falling back to keyword routing: {e}")

        # Fallback to simple keyword-based routing
        best_agent = "default_agent"
        for name, data in self.agent_registry.items():
            if name.lower() in user_query.lower():
                best_agent = name
                break
                
        return best_agent
        
    def process(self, user_query: str, **kwargs: Any) -> str:
        """Process a request with optional RAG context."""
        context = ""
        if self.retriever:
            try:
                docs = self.retriever.retrieve(user_query)
                if docs:
                    context = "Context:\n" + "\n".join(docs) + "\n\n"
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")
                
        agent_name = self.route_request(user_query)
        agent = self.agent_registry.get(agent_name)
        
        if not agent:
            return f"No suitable agent found for: {user_query}"
            
        full_query = context + "User Query: " + user_query
        # Assuming endpoint is a callable or object with a generate method
        endpoint = agent["endpoint"]
        if hasattr(endpoint, "generate"):
            return endpoint.generate([{"role": "user", "content": full_query}], **kwargs)
        elif callable(endpoint):
            return endpoint(full_query, **kwargs)
        else:
            return f"Agent {agent_name} has invalid endpoint."
