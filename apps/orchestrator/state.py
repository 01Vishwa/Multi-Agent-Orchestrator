"""
Advanced State Machine for Super Agent Orchestrator

This module implements:
1. State Machine with clear transitions (LISTENING → ROUTING → ANSWERING)
2. Parallel agent execution for reduced latency
3. Tool definitions for Django API access
4. Relevant output extraction
"""
from typing import TypedDict, List, Dict, Any, Optional, Literal
from dataclasses import dataclass, field
from enum import Enum
import operator
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class AgentState(str, Enum):
    """Super Agent State Machine States"""
    LISTENING = "listening"      # Receiving and parsing user input
    ROUTING = "routing"          # Analyzing intent and routing to agents
    EXECUTING = "executing"      # Agents processing queries
    ANSWERING = "answering"      # Synthesizing final response
    ERROR = "error"              # Error handling state
    COMPLETE = "complete"        # Terminal state


@dataclass
class AgentRequirement:
    """Requirement for a specific agent"""
    agent_name: str
    reason: str
    priority: int = 1  # 1=high, 2=medium, 3=low
    depends_on: List[str] = field(default_factory=list)
    required_context: List[str] = field(default_factory=list)


@dataclass  
class ExecutionPlan:
    """Execution plan with parallel batches"""
    batches: List[List[str]]  # Agents grouped by execution order
    dependencies: Dict[str, List[str]]
    estimated_time_ms: int = 0


class EntityType(str, Enum):
    """Types of entities that can be extracted"""
    ORDER_ID = "order_id"
    USER_ID = "user_id"
    PRODUCT_NAME = "product_name"
    TRACKING_NUMBER = "tracking_number"
    TICKET_ID = "ticket_id"
    TRANSACTION_ID = "transaction_id"
    DATE_RANGE = "date_range"
    AMOUNT = "amount"


@dataclass
class ExtractedEntity:
    """Entity extracted from user query"""
    entity_type: EntityType
    value: str
    confidence: float = 1.0
    source: str = "user_query"


class OrchestratorState(TypedDict, total=False):
    """
    Complete State Schema for the Super Agent Orchestrator.
    
    State Machine Flow:
    LISTENING → ROUTING → EXECUTING → ANSWERING → COMPLETE
                  ↓
                ERROR ────────────────────────→ COMPLETE
    """
    
    # === Current State ===
    current_state: AgentState
    state_history: List[Dict[str, Any]]  # Audit trail of state transitions
    
    # === Input Phase (LISTENING) ===
    user_query: str
    session_id: str
    conversation_history: List[BaseMessage]
    timestamp: str
    
    # === Analysis Phase (ROUTING) ===
    intent: str
    intent_confidence: float
    entities: List[ExtractedEntity]
    required_agents: List[AgentRequirement]
    complexity_score: int  # 1-10 scale
    
    # === Planning Phase ===
    execution_plan: ExecutionPlan
    parallel_batches: List[List[str]]  # Agents that can run in parallel
    
    # === Execution Phase (EXECUTING) ===
    current_batch_index: int
    agent_results: Dict[str, Dict[str, Any]]
    accumulated_context: Dict[str, Any]
    execution_times: Dict[str, float]  # Agent name → execution time in ms
    
    # === Output Phase (ANSWERING) ===
    relevant_data: Dict[str, Any]  # Filtered, relevant data only
    final_response: str
    agents_used: List[str]
    total_execution_time_ms: float
    
    # === Error Handling ===
    error: Optional[str]
    error_agent: Optional[str]
    retry_count: int


# === State Transition Functions ===

def transition_to_routing(state: OrchestratorState) -> OrchestratorState:
    """Transition from LISTENING to ROUTING"""
    state["current_state"] = AgentState.ROUTING
    state["state_history"].append({
        "from": AgentState.LISTENING,
        "to": AgentState.ROUTING,
        "trigger": "query_received"
    })
    return state


def transition_to_executing(state: OrchestratorState) -> OrchestratorState:
    """Transition from ROUTING to EXECUTING"""
    state["current_state"] = AgentState.EXECUTING
    state["state_history"].append({
        "from": AgentState.ROUTING,
        "to": AgentState.EXECUTING,
        "trigger": "plan_created"
    })
    return state


def transition_to_answering(state: OrchestratorState) -> OrchestratorState:
    """Transition from EXECUTING to ANSWERING"""
    state["current_state"] = AgentState.ANSWERING
    state["state_history"].append({
        "from": AgentState.EXECUTING,
        "to": AgentState.ANSWERING,
        "trigger": "execution_complete"
    })
    return state


def transition_to_error(state: OrchestratorState, error: str) -> OrchestratorState:
    """Transition to ERROR state"""
    previous_state = state.get("current_state", AgentState.LISTENING)
    state["current_state"] = AgentState.ERROR
    state["error"] = error
    state["state_history"].append({
        "from": previous_state,
        "to": AgentState.ERROR,
        "trigger": "error_occurred",
        "error": error
    })
    return state


def transition_to_complete(state: OrchestratorState) -> OrchestratorState:
    """Transition to terminal COMPLETE state"""
    previous_state = state.get("current_state", AgentState.ANSWERING)
    state["current_state"] = AgentState.COMPLETE
    state["state_history"].append({
        "from": previous_state,
        "to": AgentState.COMPLETE,
        "trigger": "response_ready"
    })
    return state


# === State Initialization ===

def create_initial_state(
    user_query: str,
    session_id: str,
    conversation_history: List[BaseMessage] = None
) -> OrchestratorState:
    """Create initial state in LISTENING mode"""
    from datetime import datetime
    
    return OrchestratorState(
        # Current State
        current_state=AgentState.LISTENING,
        state_history=[{
            "to": AgentState.LISTENING,
            "trigger": "session_start",
            "timestamp": datetime.utcnow().isoformat()
        }],
        
        # Input
        user_query=user_query,
        session_id=session_id,
        conversation_history=conversation_history or [],
        timestamp=datetime.utcnow().isoformat(),
        
        # Analysis (to be filled)
        intent="",
        intent_confidence=0.0,
        entities=[],
        required_agents=[],
        complexity_score=0,
        
        # Planning
        execution_plan=None,
        parallel_batches=[],
        
        # Execution
        current_batch_index=0,
        agent_results={},
        accumulated_context={},
        execution_times={},
        
        # Output
        relevant_data={},
        final_response="",
        agents_used=[],
        total_execution_time_ms=0.0,
        
        # Error handling
        error=None,
        error_agent=None,
        retry_count=0
    )


# === Parallel Execution Helpers ===

def create_parallel_execution_plan(
    required_agents: List[AgentRequirement]
) -> ExecutionPlan:
    """
    Create execution plan with parallel batches.
    
    Groups agents by dependency level:
    - Batch 0: Agents with no dependencies (run in parallel)
    - Batch 1: Agents depending on Batch 0 (run in parallel after Batch 0)
    - etc.
    """
    # Build dependency graph
    dependencies = {req.agent_name: req.depends_on for req in required_agents}
    all_agents = set(req.agent_name for req in required_agents)
    
    batches = []
    scheduled = set()
    
    while scheduled != all_agents:
        # Find agents whose dependencies are all satisfied
        current_batch = []
        for agent in all_agents - scheduled:
            deps = dependencies.get(agent, [])
            if all(dep in scheduled for dep in deps):
                current_batch.append(agent)
        
        if not current_batch:
            # Circular dependency or missing agent, schedule remaining
            current_batch = list(all_agents - scheduled)
        
        batches.append(current_batch)
        scheduled.update(current_batch)
    
    return ExecutionPlan(
        batches=batches,
        dependencies=dependencies,
        estimated_time_ms=len(batches) * 500  # Rough estimate
    )


def get_agents_for_parallel_execution(
    plan: ExecutionPlan,
    batch_index: int
) -> List[str]:
    """Get list of agents that can be executed in parallel for a given batch"""
    if batch_index < len(plan.batches):
        return plan.batches[batch_index]
    return []
