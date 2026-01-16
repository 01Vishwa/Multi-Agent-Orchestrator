"""
LangGraph Nodes for Multi-Agent Orchestrator

Each node is a function that takes state and returns updated state.
These nodes form the core logic of the orchestration workflow.
"""
import json
import logging
import time
from typing import List, Dict, Any
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from django.conf import settings

from .state import (
    OrchestratorState,
    AgentResult,
    EntityInfo,
    AgentTask,
    INTENT_CATEGORIES,
    AGENT_CAPABILITIES,
    DEPENDENCY_PATTERNS,
)

logger = logging.getLogger(__name__)


def get_llm():
    """Get the configured LLM instance using GitHub Models API."""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.GITHUB_TOKEN,
        base_url=settings.LLM_BASE_URL,
        temperature=0.1,  # Low temperature for consistency
    )


# ============================================================================
# NODE: Analyze Query
# ============================================================================

ANALYZE_PROMPT = """You are an intent classifier for a multi-product e-commerce platform.
The platform has 4 products:
1. ShopCore - E-commerce (orders, products, users)
2. ShipStream - Logistics (shipments, tracking, warehouses)
3. PayGuard - FinTech (wallets, transactions, refunds)
4. CareDesk - Customer Support (tickets, messages, surveys)

Analyze the following customer query and extract:
1. The primary intent (what they want to do)
2. Entities mentioned (product names, order IDs, etc.)
3. Which agents (products) are needed to answer this query

Customer Query: {query}

Conversation History:
{history}

Respond in JSON format:
{{
    "intent": "one of: order_status, delivery_tracking, refund_status, refund_request, ticket_status, ticket_create, payment_issue, wallet_balance, product_inquiry, account_info, general_query, multi_domain",
    "intent_confidence": 0.0 to 1.0,
    "entities": [
        {{"entity_type": "type", "value": "value", "confidence": 0.0 to 1.0}}
    ],
    "required_agents": ["list of: shopcore, shipstream, payguard, caredesk"],
    "reasoning": "brief explanation of your analysis"
}}
"""


def analyze_query(state: OrchestratorState) -> Dict[str, Any]:
    """
    Analyze the user query to determine intent, extract entities,
    and identify which agents are needed.
    """
    logger.info(f"Analyzing query: {state['user_query'][:100]}...")
    
    llm = get_llm()
    
    # Format conversation history
    history_str = ""
    if state.get('conversation_history'):
        for msg in state['conversation_history'][-5:]:  # Last 5 messages
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_str += f"{role}: {content}\n"
    else:
        history_str = "No previous conversation"
    
    prompt = ANALYZE_PROMPT.format(
        query=state['user_query'],
        history=history_str
    )
    
    try:
        response = llm.invoke([
            SystemMessage(content="You are a precise intent classifier. Always respond in valid JSON."),
            HumanMessage(content=prompt)
        ])
        
        # Parse the response
        content = response.content
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        result = json.loads(content)
        
        # Convert entities to proper format
        entities = [
            EntityInfo(
                entity_type=e.get('entity_type', 'unknown'),
                value=e.get('value', ''),
                confidence=e.get('confidence', 0.5)
            )
            for e in result.get('entities', [])
        ]
        
        logger.info(f"Intent detected: {result.get('intent')} with confidence {result.get('intent_confidence')}")
        logger.info(f"Required agents: {result.get('required_agents')}")
        
        return {
            "intent": result.get('intent', 'general_query'),
            "intent_confidence": result.get('intent_confidence', 0.5),
            "entities": entities,
            "required_agents": result.get('required_agents', ['shopcore']),
            "status": "analyzing",
        }
        
    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        return {
            "intent": "general_query",
            "intent_confidence": 0.3,
            "entities": [],
            "required_agents": ["shopcore"],  # Default to shopcore
            "status": "analyzing",
            "error_message": str(e),
        }


# ============================================================================
# NODE: Create Execution Plan
# ============================================================================

def create_execution_plan(state: OrchestratorState) -> Dict[str, Any]:
    """
    Create an ordered execution plan based on required agents and dependencies.
    """
    logger.info(f"Creating execution plan for agents: {state['required_agents']}")
    
    required = set(state['required_agents'])
    
    # Build dependency graph
    dependency_graph = {}
    for agent in required:
        deps = [d for d in DEPENDENCY_PATTERNS.get(agent, []) if d in required]
        dependency_graph[agent] = deps
    
    # Topological sort for execution order
    execution_order = []
    visited = set()
    temp_visited = set()
    
    def visit(agent):
        if agent in temp_visited:
            # Circular dependency - just continue
            return
        if agent in visited:
            return
        
        temp_visited.add(agent)
        for dep in dependency_graph.get(agent, []):
            visit(dep)
        temp_visited.remove(agent)
        visited.add(agent)
        execution_order.append(agent)
    
    for agent in required:
        visit(agent)
    
    # Create tasks with proper ordering
    execution_plan = []
    entities_context = {e['entity_type']: e['value'] for e in state.get('entities', [])}
    
    for priority, agent in enumerate(execution_order):
        task = AgentTask(
            agent_name=agent,
            task_description=f"Query {agent} database to help answer: {state['user_query']}",
            depends_on=dependency_graph.get(agent, []),
            context=entities_context,
            priority=priority
        )
        execution_plan.append(task)
    
    logger.info(f"Execution order: {execution_order}")
    
    return {
        "execution_plan": execution_plan,
        "dependency_graph": dependency_graph,
        "pending_agents": list(execution_order),
        "completed_agents": [],
        "status": "planning",
    }


# ============================================================================
# NODE: Execute Agents
# ============================================================================

def execute_agents(state: OrchestratorState) -> Dict[str, Any]:
    """
    Execute the next agent(s) in the execution plan.
    This handles both sequential (dependent) and parallel (independent) execution.
    """
    from apps.shopcore.agent import ShopCoreAgent
    from apps.shipstream.agent import ShipStreamAgent
    from apps.payguard.agent import PayGuardAgent
    from apps.caredesk.agent import CareDeSkAgent
    
    logger.info(f"Executing agents. Pending: {state['pending_agents']}")
    
    if not state['pending_agents']:
        return {"status": "synthesizing"}
    
    # Get agents that can be executed (all dependencies satisfied)
    completed = set(state['completed_agents'])
    ready_agents = []
    
    for agent_name in state['pending_agents']:
        deps = state['dependency_graph'].get(agent_name, [])
        if all(d in completed for d in deps):
            ready_agents.append(agent_name)
    
    if not ready_agents:
        logger.warning("No agents ready to execute - possible circular dependency")
        return {
            "status": "error",
            "error_message": "No agents ready to execute"
        }
    
    # Agent instances
    agents = {
        "shopcore": ShopCoreAgent(),
        "shipstream": ShipStreamAgent(),
        "payguard": PayGuardAgent(),
        "caredesk": CareDeSkAgent(),
    }
    
    # Execute ready agents
    results = []
    new_context = dict(state.get('accumulated_context', {}))
    
    for agent_name in ready_agents:
        agent = agents.get(agent_name)
        if not agent:
            logger.error(f"Unknown agent: {agent_name}")
            continue
        
        # Find the task for this agent
        task = next(
            (t for t in state['execution_plan'] if t['agent_name'] == agent_name),
            None
        )
        
        if not task:
            continue
        
        # Merge context from previous agents
        task_context = {**task['context'], **new_context}
        
        logger.info(f"Executing {agent_name} with context: {task_context}")
        
        start_time = time.time()
        try:
            result = agent.execute(
                query=state['user_query'],
                context=task_context,
                entities=state.get('entities', [])
            )
            execution_time = int((time.time() - start_time) * 1000)
            
            agent_result = AgentResult(
                agent_name=agent_name,
                success=result.get('success', False),
                data=result.get('data', {}),
                sql_query=result.get('sql_query'),
                error=result.get('error'),
                execution_time_ms=execution_time
            )
            results.append(agent_result)
            
            # Update context with results from this agent
            if result.get('success') and result.get('data'):
                new_context[f"{agent_name}_result"] = result['data']
                
                # Extract key IDs for subsequent agents
                data = result['data']
                if isinstance(data, list) and len(data) > 0:
                    first = data[0] if isinstance(data[0], dict) else {}
                    for key in ['order_id', 'user_id', 'tracking_number', 'ticket_id']:
                        if key in first:
                            new_context[key] = first[key]
                elif isinstance(data, dict):
                    for key in ['order_id', 'user_id', 'tracking_number', 'ticket_id']:
                        if key in data:
                            new_context[key] = data[key]
            
            logger.info(f"{agent_name} completed in {execution_time}ms")
            
        except Exception as e:
            logger.error(f"Error executing {agent_name}: {e}")
            results.append(AgentResult(
                agent_name=agent_name,
                success=False,
                data={},
                sql_query=None,
                error=str(e),
                execution_time_ms=0
            ))
    
    # Update pending/completed lists
    new_pending = [a for a in state['pending_agents'] if a not in ready_agents]
    new_completed = state['completed_agents'] + ready_agents
    
    # Determine next status
    next_status = "executing" if new_pending else "synthesizing"
    
    return {
        "agent_results": results,
        "pending_agents": new_pending,
        "completed_agents": new_completed,
        "accumulated_context": new_context,
        "status": next_status,
    }


# ============================================================================
# NODE: Synthesize Response
# ============================================================================

SYNTHESIZE_PROMPT = """You are a helpful customer support assistant for OmniLife, a multi-product e-commerce platform.

Based on the query results from our internal systems, synthesize a clear, helpful response for the customer.

Customer Query: {query}

Data Retrieved:
{agent_data}

Guidelines:
1. Be conversational and friendly
2. Directly answer the customer's question
3. Include specific details (order IDs, tracking numbers, dates, amounts)
4. If some information is missing, acknowledge it and offer next steps
5. Don't mention internal system names (ShopCore, ShipStream, etc.)
6. Keep the response concise but complete

Respond with a natural, helpful message for the customer.
"""


def synthesize_response(state: OrchestratorState) -> Dict[str, Any]:
    """
    Synthesize a natural language response from all agent results.
    """
    logger.info("Synthesizing final response")
    
    llm = get_llm()
    
    # Format agent results for the prompt
    agent_data_parts = []
    for result in state.get('agent_results', []):
        if result['success']:
            agent_data_parts.append(f"From {result['agent_name']}:\n{json.dumps(result['data'], indent=2, default=str)}")
        else:
            agent_data_parts.append(f"From {result['agent_name']}: Error - {result['error']}")
    
    agent_data = "\n\n".join(agent_data_parts) if agent_data_parts else "No data retrieved"
    
    prompt = SYNTHESIZE_PROMPT.format(
        query=state['user_query'],
        agent_data=agent_data
    )
    
    try:
        response = llm.invoke([
            SystemMessage(content="You are a helpful customer support assistant."),
            HumanMessage(content=prompt)
        ])
        
        final_response = response.content
        
        logger.info(f"Response synthesized: {final_response[:100]}...")
        
        return {
            "final_response": final_response,
            "response_confidence": 0.9 if all(r['success'] for r in state.get('agent_results', [])) else 0.6,
            "status": "complete",
            "end_time": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error synthesizing response: {e}")
        
        # Fallback response
        return {
            "final_response": "I apologize, but I'm having trouble processing your request right now. "
                             "Please try again or contact our support team directly.",
            "response_confidence": 0.3,
            "status": "complete",
            "end_time": datetime.utcnow().isoformat(),
            "error_message": str(e),
        }


# ============================================================================
# NODE: Handle Error
# ============================================================================

def handle_error(state: OrchestratorState) -> Dict[str, Any]:
    """
    Handle errors gracefully and return a user-friendly message.
    """
    logger.error(f"Handling error: {state.get('error_message')}")
    
    return {
        "final_response": "I apologize, but I encountered an issue while processing your request. "
                         f"Error: {state.get('error_message', 'Unknown error')}. "
                         "Please try again or contact our support team.",
        "status": "complete",
        "end_time": datetime.utcnow().isoformat(),
    }
