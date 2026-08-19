from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from typing import TypedDict, Annotated, Sequence
import operator

# 1. Define the State (The "Context" passed between nodes)
class NESState(TypedDict):
    messages: Annotated[Sequence, operator.add]
    next_action: str

# 2. Define the Nodes (The "Steps" in your BPMN process)
def router_node(state: NESState):
    """The Cognitive Core: Decides what to do next."""
    # In production, this is where your fine-tuned Qwen model is called 
    # via the Ollama API to analyze the messages and decide the next tool.
    user_input = state["messages"][-1].content.lower()
    
    if "email" in user_input or "mail" in user_input:
        return {"next_action": "email_agent"}
    elif "linkedin" in user_input or "post" in user_input:
        return {"next_action": "social_agent"}
    elif "track" in user_input or "conversion" in user_input:
        return {"next_action": "analytics_agent"}
    else:
        return {"next_action": "general_chat"}

def email_node(state: NESState):
    print("-> Routing to Email Sub-Agent...")
    # Logic to execute email tools
    return {"messages": ["Email workflow executed."]}

def social_node(state: NESState):
    print("-> Routing to Social Media Sub-Agent...")
    # Logic to execute social tools
    return {"messages": ["Social workflow executed."]}

def analytics_node(state: NESState):
    print("-> Routing to Analytics Sub-Agent...")
    # Logic to execute tracking tools
    return {"messages": ["Analytics workflow executed."]}

# 3. Build the Graph
workflow = StateGraph(NESState)

# Add nodes
workflow.add_node("router", router_node)
workflow.add_node("email_agent", email_node)
workflow.add_node("social_agent", social_node)
workflow.add_node("analytics_agent", analytics_node)

# Define edges (The workflow logic)
workflow.set_entry_point("router")

# Conditional routing based on the router's decision
workflow.add_conditional_edges(
    "router",
    lambda state: state["next_action"],
    {
        "email_agent": "email_agent",
        "social_agent": "social_agent",
        "analytics_agent": "analytics_agent",
        "general_chat": END
    }
)

# All sub-agents end the graph after execution
workflow.add_edge("email_agent", END)
workflow.add_edge("social_agent", END)
workflow.add_edge("analytics_agent", END)

# Compile the graph
nes_app = workflow.compile()

# --- Execution Test ---
if __name__ == "__main__":
    initial_state = {"messages": [HumanMessage(content="Sort my unread emails and draft replies for Trident Group.")]}
    final_state = nes_app.invoke(initial_state)
    print("Final State:", final_state)