"""
LangGraph Workflow Definition for Multi-Agent Orchestrator

This module defines the complete LangGraph workflow that orchestrates
multiple specialized agents to handle complex customer queries.
"""
import logging
from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import OrchestratorState, create_initial_state
from .nodes import (
    analyze_query,
    create_execution_plan,
    execute_agents,
    synthesize_response,
    handle_error,
)

logger = logging.getLogger(__name__)


def should_continue_execution(state: OrchestratorState) -> Literal["execute", "synthesize", "error"]:
    """
    Conditional edge: Determine if we should continue executing agents or move to synthesis.
    """
    if state.get('status') == 'error':
        return "error"
    
    if state.get('pending_agents'):
        return "execute"
    
    return "synthesize"


def route_after_analysis(state: OrchestratorState) -> Literal["plan", "error"]:
    """
    Conditional edge: Route after query analysis.
    """
    if state.get('status') == 'error' or not state.get('required_agents'):
        return "error"
    return "plan"


def build_orchestrator_graph():
    """
    Build and compile the LangGraph workflow.
    
    Workflow:
    1. analyze_query: Parse intent, extract entities, identify required agents
    2. create_execution_plan: Create ordered execution plan with dependencies
    3. execute_agents: Execute agents in dependency order (loop)
    4. synthesize_response: Combine results into natural language response
    
    Graph Structure:
    
        START
          │
          ▼
      ┌─────────┐
      │ Analyze │
      └────┬────┘
           │
           ▼
       ┌──────┐
       │ Plan │
       └──┬───┘
          │
          ▼
      ┌─────────┐◄──────┐
      │ Execute │       │ (loop while pending)
      └────┬────┘───────┘
           │
           ▼
     ┌───────────┐
     │ Synthesize│
     └─────┬─────┘
           │
           ▼
          END
    """
    # Create the graph with our state schema
    graph = StateGraph(OrchestratorState)
    
    # Add nodes
    graph.add_node("analyze", analyze_query)
    graph.add_node("plan", create_execution_plan)
    graph.add_node("execute", execute_agents)
    graph.add_node("synthesize", synthesize_response)
    graph.add_node("error", handle_error)
    
    # Add edges
    # START -> analyze
    graph.add_edge(START, "analyze")
    
    # analyze -> plan or error
    graph.add_conditional_edges(
        "analyze",
        route_after_analysis,
        {
            "plan": "plan",
            "error": "error"
        }
    )
    
    # plan -> execute
    graph.add_edge("plan", "execute")
    
    # execute -> execute (loop) or synthesize or error
    graph.add_conditional_edges(
        "execute",
        should_continue_execution,
        {
            "execute": "execute",
            "synthesize": "synthesize",
            "error": "error"
        }
    )
    
    # synthesize -> END
    graph.add_edge("synthesize", END)
    
    # error -> END
    graph.add_edge("error", END)
    
    # Compile with memory checkpointer for conversation persistence
    memory = MemorySaver()
    compiled_graph = graph.compile(checkpointer=memory)
    
    logger.info("Orchestrator graph compiled successfully")
    
    return compiled_graph


# Create a singleton instance
_graph_instance = None


def get_orchestrator_graph():
    """
    Get the singleton orchestrator graph instance.
    """
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_orchestrator_graph()
    return _graph_instance


class OrchestratorService:
    """
    High-level service for orchestrating multi-agent queries.
    """
    
    def __init__(self):
        self.graph = get_orchestrator_graph()
    
    def process_query(
        self,
        query: str,
        session_id: str,
        user_id: str = None,
        conversation_history: list = None
    ) -> dict:
        """
        Process a customer query through the multi-agent pipeline.
        
        Args:
            query: Natural language customer query
            session_id: Unique session identifier for conversation tracking
            user_id: Optional user identifier if authenticated
            conversation_history: Optional list of previous messages
            
        Returns:
            dict with:
                - response: Natural language response
                - agents_used: List of agents that were consulted
                - success: Whether the query was processed successfully
                - execution_details: Detailed execution information
        """
        logger.info(f"Processing query: {query[:100]}...")
        
        # Create initial state
        initial_state = create_initial_state(
            user_query=query,
            session_id=session_id,
            user_id=user_id,
            conversation_history=conversation_history
        )
        
        # Configuration for the graph execution
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }
        
        try:
            # Run the graph
            final_state = self.graph.invoke(initial_state, config)
            
            # Extract results
            return {
                "response": final_state.get("final_response", ""),
                "agents_used": final_state.get("completed_agents", []),
                "success": final_state.get("status") == "complete" and not final_state.get("error_message"),
                "intent": final_state.get("intent"),
                "intent_confidence": final_state.get("intent_confidence"),
                "execution_details": {
                    "agent_results": final_state.get("agent_results", []),
                    "execution_time": {
                        "start": final_state.get("start_time"),
                        "end": final_state.get("end_time"),
                    },
                    "entities_found": final_state.get("entities", []),
                },
                "error": final_state.get("error_message"),
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "response": "I apologize, but I encountered an unexpected error. Please try again.",
                "agents_used": [],
                "success": False,
                "intent": None,
                "intent_confidence": 0,
                "execution_details": {},
                "error": str(e),
            }
    
    def get_conversation_history(self, session_id: str) -> list:
        """
        Get the conversation history for a session.
        """
        # This would retrieve from the checkpointer
        # For now, return empty list
        return []
