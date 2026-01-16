"""
LangGraph Workflow with State Machine and Parallel Execution

This module implements:
1. StateGraph with clear state transitions
2. Conditional edges based on state machine
3. Memory checkpointing for conversation context
4. Optimized execution flow

State Machine Flow:
    LISTENING → ROUTING → EXECUTING → ANSWERING → COMPLETE
                   ↓
                 ERROR ────────────────────────→ COMPLETE
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import (
    OrchestratorState, AgentState, create_initial_state,
    create_parallel_execution_plan
)
from .nodes import (
    analyze_query,
    create_execution_plan,
    execute_agents_parallel,
    synthesize_response,
    handle_error,
    route_after_analysis,
    should_continue_execution
)

logger = logging.getLogger(__name__)


# =============================================================================
# GRAPH ROUTING FUNCTIONS
# =============================================================================

def route_from_analysis(state: OrchestratorState) -> str:
    """
    Route after query analysis (ROUTING state).
    Returns next node based on analysis results.
    """
    if state.get("error"):
        logger.warning("[ROUTER] Error detected, routing to error handler")
        return "handle_error"
    
    confidence = state.get("intent_confidence", 0)
    required_agents = state.get("required_agents", [])
    
    if confidence < 0.2 or not required_agents:
        logger.warning(f"[ROUTER] Low confidence ({confidence}) or no agents, routing to error")
        return "handle_error"
    
    logger.info(f"[ROUTER] Analysis complete, routing to planning")
    return "create_plan"


def route_from_execution(state: OrchestratorState) -> str:
    """
    Route after agent execution (EXECUTING state).
    """
    if state.get("error"):
        return "handle_error"
    
    agent_results = state.get("agent_results", {})
    
    if not agent_results:
        logger.warning("[ROUTER] No agent results, routing to error")
        return "handle_error"
    
    # Check if any agent succeeded
    any_success = any(r.get("success") for r in agent_results.values())
    
    if not any_success:
        logger.warning("[ROUTER] All agents failed, routing to error")
        return "handle_error"
    
    logger.info("[ROUTER] Execution complete, routing to synthesis")
    return "synthesize"


def route_from_error(state: OrchestratorState) -> str:
    """Route from error handling."""
    return END


def is_complete(state: OrchestratorState) -> str:
    """Check if workflow is complete."""
    current_state = state.get("current_state")
    if current_state == AgentState.COMPLETE:
        return END
    return "continue"


# =============================================================================
# GRAPH DEFINITION
# =============================================================================

def create_orchestrator_graph() -> StateGraph:
    """
    Create the LangGraph workflow with state machine transitions.
    
    Graph Structure:
    
    START
      │
      ▼
    analyze_query (LISTENING → ROUTING)
      │
      ├─── error ──→ handle_error
      │
      ▼
    create_plan (Plan parallel batches)
      │
      ▼
    execute_agents (ROUTING → EXECUTING)
      │
      ├─── error ──→ handle_error
      │
      ▼
    synthesize (EXECUTING → ANSWERING → COMPLETE)
      │
      ▼
     END
    """
    
    # Create graph with state schema
    workflow = StateGraph(OrchestratorState)
    
    # Add nodes
    workflow.add_node("analyze", analyze_query)
    workflow.add_node("create_plan", create_execution_plan)
    workflow.add_node("execute", execute_agents_parallel)
    workflow.add_node("synthesize", synthesize_response)
    workflow.add_node("handle_error", handle_error)
    
    # Set entry point
    workflow.set_entry_point("analyze")
    
    # Add conditional edges from analysis
    workflow.add_conditional_edges(
        "analyze",
        route_from_analysis,
        {
            "create_plan": "create_plan",
            "handle_error": "handle_error"
        }
    )
    
    # Linear edge from plan to execute
    workflow.add_edge("create_plan", "execute")
    
    # Add conditional edges from execution
    workflow.add_conditional_edges(
        "execute",
        route_from_execution,
        {
            "synthesize": "synthesize",
            "handle_error": "handle_error"
        }
    )
    
    # Terminal edges
    workflow.add_edge("synthesize", END)
    workflow.add_edge("handle_error", END)
    
    return workflow


# Create compiled graph with memory checkpointing
memory = MemorySaver()
orchestrator_graph = create_orchestrator_graph().compile(checkpointer=memory)


# =============================================================================
# ORCHESTRATOR SERVICE
# =============================================================================

class OrchestratorService:
    """
    High-level service for processing user queries through the orchestrator.
    
    Usage:
        service = OrchestratorService()
        result = service.process_query("Where is my order?", session_id="sess123")
    """
    
    def __init__(self):
        self.graph = orchestrator_graph
        logger.info("[SERVICE] OrchestratorService initialized")
    
    def process_query(
        self,
        query: str,
        session_id: str,
        conversation_history: list = None
    ) -> Dict[str, Any]:
        """
        Process a user query through the multi-agent orchestrator.
        
        Args:
            query: User's natural language query
            session_id: Session identifier for conversation continuity
            conversation_history: Optional list of previous messages
            
        Returns:
            Dictionary with response and metadata
        """
        start_time = datetime.utcnow()
        logger.info(f"[SERVICE] Processing query: {query[:50]}...")
        
        # Create initial state
        initial_state = create_initial_state(
            user_query=query,
            session_id=session_id,
            conversation_history=conversation_history
        )
        
        # Configure thread for memory checkpointing
        config = {
            "configurable": {
                "thread_id": session_id
            }
        }
        
        try:
            # Execute the graph
            final_state = self.graph.invoke(initial_state, config)
            
            # Build response
            response = {
                "success": True,
                "response": final_state.get("final_response", ""),
                "session_id": session_id,
                "intent": final_state.get("intent", ""),
                "intent_confidence": final_state.get("intent_confidence", 0),
                "agents_used": final_state.get("agents_used", []),
                "execution_details": {
                    "state_history": self._format_state_history(final_state.get("state_history", [])),
                    "execution_times": final_state.get("execution_times", {}),
                    "parallel_batches": final_state.get("parallel_batches", []),
                    "agent_results": self._format_agent_results(final_state.get("agent_results", {}))
                },
                "total_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
            }
            
            logger.info(f"[SERVICE] Query processed in {response['total_time_ms']:.0f}ms")
            return response
            
        except Exception as e:
            logger.error(f"[SERVICE] Error processing query: {e}")
            return {
                "success": False,
                "response": f"I apologize, but I encountered an error: {str(e)}",
                "session_id": session_id,
                "error": str(e),
                "agents_used": [],
                "total_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
            }
    
    def _format_state_history(self, history: list) -> list:
        """Format state history for API response."""
        formatted = []
        for entry in history:
            formatted.append({
                "from_state": entry.get("from", "start"),
                "to_state": str(entry.get("to", "")),
                "trigger": entry.get("trigger", "")
            })
        return formatted
    
    def _format_agent_results(self, results: dict) -> list:
        """Format agent results for API response."""
        formatted = []
        for agent_name, result in results.items():
            formatted.append({
                "agent_name": agent_name,
                "success": result.get("success", False),
                "data": result.get("data", []),
                "execution_time_ms": result.get("execution_time_ms", 0),
                "error": result.get("error")
            })
        return formatted
    
    def get_available_tools(self) -> list:
        """Get list of available tools for documentation."""
        from .nodes import AVAILABLE_TOOLS
        
        tools_info = []
        for tool in AVAILABLE_TOOLS:
            tools_info.append({
                "name": tool.name,
                "description": tool.description
            })
        return tools_info


# Create singleton service instance
orchestrator_service = OrchestratorService()
