"""
LangGraph State Schema for Multi-Agent Orchestrator

This module defines the typed state that flows through the LangGraph workflow.
The state captures the entire lifecycle of a customer query from analysis to response.
"""
from typing import TypedDict, List, Optional, Literal, Annotated, Any
from operator import add
from dataclasses import dataclass, field
from datetime import datetime


class AgentResult(TypedDict):
    """
    Result returned by a sub-agent after execution.
    """
    agent_name: str              # Name of the agent (shopcore, shipstream, payguard, caredesk)
    success: bool                # Whether the agent execution was successful
    data: Any                    # Actual data returned (query results)
    sql_query: Optional[str]     # The SQL query that was generated and executed
    error: Optional[str]         # Error message if execution failed
    execution_time_ms: int       # Time taken to execute in milliseconds


class EntityInfo(TypedDict):
    """
    Entity extracted from the user query.
    """
    entity_type: str            # Type: user_id, order_id, product_name, tracking_number, etc.
    value: str                  # The actual value
    confidence: float           # Confidence score 0-1


class AgentTask(TypedDict):
    """
    A task to be executed by a specific agent.
    """
    agent_name: str             # Target agent
    task_description: str       # Natural language description of what to do
    depends_on: List[str]       # List of agent names this task depends on
    context: dict               # Additional context from previous agent results
    priority: int               # Execution priority (lower = higher priority)


class OrchestratorState(TypedDict):
    """
    Complete state for the orchestrator workflow.
    This state is passed through all nodes in the LangGraph.
    """
    # === Input ===
    user_query: str                     # Original natural language query from user
    session_id: str                     # Conversation session ID
    user_id: Optional[str]              # User ID if authenticated
    conversation_history: List[dict]    # Previous messages in conversation
    
    # === Analysis Phase ===
    intent: str                         # Detected intent (order_status, refund_check, ticket_status, etc.)
    intent_confidence: float            # Confidence in intent detection
    entities: List[EntityInfo]          # Extracted entities (product names, order IDs, etc.)
    required_agents: List[str]          # Agents needed (shopcore, shipstream, payguard, caredesk)
    
    # === Planning Phase ===
    execution_plan: List[AgentTask]     # Ordered list of agent tasks
    dependency_graph: dict              # Agent dependencies {agent: [depends_on]}
    
    # === Execution Phase ===
    current_step: int                   # Current step in execution plan
    agent_results: Annotated[List[AgentResult], add]  # Results from all agents (accumulated)
    pending_agents: List[str]           # Agents still to execute
    completed_agents: List[str]         # Agents that have completed
    
    # === Context Accumulation ===
    accumulated_context: dict           # Context built up from agent results for subsequent agents
    
    # === Output Phase ===
    final_response: Optional[str]       # Synthesized natural language response
    response_confidence: float          # Confidence in the response
    
    # === Metadata ===
    status: Literal["initialized", "analyzing", "planning", "executing", "synthesizing", "complete", "error"]
    error_message: Optional[str]        # Error message if status is 'error'
    start_time: str                     # ISO timestamp when processing started
    end_time: Optional[str]             # ISO timestamp when processing completed
    total_tokens_used: int              # Total LLM tokens consumed


def create_initial_state(
    user_query: str,
    session_id: str,
    user_id: Optional[str] = None,
    conversation_history: Optional[List[dict]] = None
) -> OrchestratorState:
    """
    Create an initial state for a new query.
    """
    return OrchestratorState(
        # Input
        user_query=user_query,
        session_id=session_id,
        user_id=user_id,
        conversation_history=conversation_history or [],
        
        # Analysis (to be filled)
        intent="",
        intent_confidence=0.0,
        entities=[],
        required_agents=[],
        
        # Planning (to be filled)
        execution_plan=[],
        dependency_graph={},
        
        # Execution
        current_step=0,
        agent_results=[],
        pending_agents=[],
        completed_agents=[],
        
        # Context
        accumulated_context={},
        
        # Output
        final_response=None,
        response_confidence=0.0,
        
        # Metadata
        status="initialized",
        error_message=None,
        start_time=datetime.utcnow().isoformat(),
        end_time=None,
        total_tokens_used=0
    )


# Intent categories for classification
INTENT_CATEGORIES = [
    "order_status",           # Where is my order?
    "delivery_tracking",      # Track my package
    "refund_status",          # Check refund status
    "refund_request",         # Request a refund
    "ticket_status",          # Check support ticket status
    "ticket_create",          # Create a new ticket
    "payment_issue",          # Payment problems
    "wallet_balance",         # Check wallet balance
    "product_inquiry",        # Product questions
    "account_info",           # Account information
    "general_query",          # General questions
    "multi_domain",           # Complex queries spanning multiple domains
]

# Agent capabilities mapping
AGENT_CAPABILITIES = {
    "shopcore": [
        "order_status",
        "product_inquiry",
        "account_info",
        "order_search",
        "user_lookup",
    ],
    "shipstream": [
        "delivery_tracking",
        "shipment_status",
        "warehouse_info",
        "tracking_history",
    ],
    "payguard": [
        "refund_status",
        "refund_request",
        "payment_issue",
        "wallet_balance",
        "transaction_history",
    ],
    "caredesk": [
        "ticket_status",
        "ticket_create",
        "ticket_history",
        "survey_feedback",
    ],
}

# Common dependency patterns
DEPENDENCY_PATTERNS = {
    # To check shipment, we often need order_id first
    "shipstream": ["shopcore"],
    # To check refund, we often need order_id first
    "payguard": ["shopcore"],
    # Ticket can reference orders, so might need order_id
    "caredesk": ["shopcore"],
}
