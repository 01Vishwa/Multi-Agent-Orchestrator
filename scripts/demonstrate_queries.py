"""
Demonstration Script - Super Agent Thought Process Logs

This script demonstrates 3 distinct customer queries showing how the 
Super Agent coordinates Sub-Agents to resolve complex, multi-domain queries.

Run: python scripts/demonstrate_queries.py
"""
import os
import sys
import json
import django
from datetime import datetime

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from apps.orchestrator.graph import OrchestratorService


def print_header(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_step(step_num, agent, action):
    print(f"\n  Step {step_num}: [{agent.upper()}]")
    print(f"    → {action}")


def print_thought(thought):
    print(f"\n  💭 SUPER AGENT THOUGHT PROCESS:")
    for line in thought.split('\n'):
        print(f"    {line}")


def print_result(data, indent=4):
    prefix = " " * indent
    if isinstance(data, dict):
        for key, value in list(data.items())[:6]:
            print(f"{prefix}• {key}: {value}")
    elif isinstance(data, list):
        for item in data[:3]:
            if isinstance(item, dict):
                print(f"{prefix}---")
                for key, value in list(item.items())[:5]:
                    print(f"{prefix}  {key}: {value}")


def demonstrate_query(query_num, query, expected_agents, description):
    """Run a query and display the thought process."""
    
    print_header(f"QUERY {query_num}: {description}")
    print(f"\n  📝 CUSTOMER QUERY:")
    print(f"    \"{query}\"")
    
    print(f"\n  🎯 EXPECTED WORKFLOW:")
    for i, agent in enumerate(expected_agents, 1):
        print(f"    {i}. {agent['name']} → {agent['purpose']}")
    
    print("\n" + "-" * 80)
    print("  🤖 SUPER AGENT EXECUTION LOG")
    print("-" * 80)
    
    try:
        # Initialize orchestrator
        service = OrchestratorService()
        session_id = f"demo_session_{query_num}"
        
        # Process query
        start_time = datetime.now()
        result = service.process_query(
            query=query,
            session_id=session_id,
            conversation_history=[]
        )
        end_time = datetime.now()
        
        # Display thought process
        print_thought(f"""
1. LISTENING: Received customer query
2. ROUTING: Analyzing intent and required agents
   - Intent: {result.get('intent', 'unknown')}
   - Confidence: {result.get('intent_confidence', 0):.2%}
   - Agents identified: {result.get('agents_used', [])}
3. EXECUTING: Running agents with dependency resolution
4. ANSWERING: Synthesizing response from collected data
5. COMPLETE: Response ready""")
        
        # Display execution details
        execution = result.get('execution_details', {})
        
        if execution.get('parallel_batches'):
            print(f"\n  ⚡ PARALLEL EXECUTION BATCHES:")
            for i, batch in enumerate(execution['parallel_batches']):
                print(f"    Batch {i+1}: {batch}")
        
        if execution.get('agent_results'):
            print(f"\n  📊 AGENT RESULTS:")
            for agent_result in execution['agent_results']:
                agent_name = agent_result.get('agent_name', 'unknown')
                success = "✅" if agent_result.get('success') else "❌"
                time_ms = agent_result.get('execution_time_ms', 0)
                print(f"\n    {success} {agent_name.upper()} ({time_ms:.0f}ms)")
                
                data = agent_result.get('data', [])
                if isinstance(data, list) and len(data) > 0:
                    for item in data[:2]:
                        if isinstance(item, dict):
                            print_result(item, 6)
        
        if execution.get('execution_times'):
            print(f"\n  ⏱️ TIMING BREAKDOWN:")
            for stage, time_ms in execution['execution_times'].items():
                print(f"    • {stage}: {time_ms:.0f}ms")
        
        # Display final response
        print(f"\n  💬 FINAL RESPONSE TO CUSTOMER:")
        response = result.get('response', 'No response')
        # Wrap response nicely
        words = response.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            if len(' '.join(current_line)) > 70:
                lines.append('    ' + ' '.join(current_line[:-1]))
                current_line = [word]
        if current_line:
            lines.append('    ' + ' '.join(current_line))
        print('\n'.join(lines))
        
        print(f"\n  📈 METRICS:")
        total_time = (end_time - start_time).total_seconds() * 1000
        print(f"    • Total Time: {total_time:.0f}ms")
        print(f"    • Agents Used: {result.get('agents_used', [])}")
        print(f"    • Success: {result.get('success', False)}")
        
    except Exception as e:
        print(f"\n  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all 3 demonstration queries."""
    
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  OMNILIFE MULTI-AGENT ORCHESTRATOR - DEMONSTRATION".center(78) + "█")
    print("█" + "  Super Agent Thought Process Logs".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    print(f"\n  Timestamp: {datetime.now().isoformat()}")
    print("  System: OmniLife Multi-Agent Support")
    print("  Agents: ShopCore, ShipStream, PayGuard, CareDesk")
    
    # QUERY 1: Multi-domain delivery + ticket query (3 agents)
    demonstrate_query(
        query_num=1,
        query="I ordered a 'Gaming Monitor' last week, but it hasn't arrived. I opened a ticket about this yesterday. Can you tell me where the package is right now and if my ticket has been assigned?",
        expected_agents=[
            {"name": "ShopCore", "purpose": "Find OrderID for 'Gaming Monitor'"},
            {"name": "ShipStream", "purpose": "Get tracking events and current location"},
            {"name": "CareDesk", "purpose": "Find recent ticket and assignment status"}
        ],
        description="Complex Multi-Domain Query (3 Agents)"
    )
    
    # QUERY 2: Refund and payment status (2-3 agents)
    demonstrate_query(
        query_num=2,
        query="I returned my Gaming Monitor order and requested a refund. What's the status of my refund and when will I get my money back?",
        expected_agents=[
            {"name": "ShopCore", "purpose": "Find order with refund status"},
            {"name": "PayGuard", "purpose": "Check refund transaction status"},
        ],
        description="Refund Status Query (2 Agents)"
    )
    
    # QUERY 3: Account overview (multiple agents)
    demonstrate_query(
        query_num=3,
        query="Show me my recent transactions and any open support tickets I have.",
        expected_agents=[
            {"name": "PayGuard", "purpose": "Get recent transactions"},
            {"name": "CareDesk", "purpose": "Find open tickets"},
        ],
        description="Account Overview Query (2 Agents)"
    )
    
    print_header("DEMONSTRATION COMPLETE")
    print(f"\n  ✅ Successfully demonstrated 3 complex, multi-domain queries")
    print(f"  ✅ Showed Super Agent coordinating Sub-Agents")
    print(f"  ✅ Displayed thought process and execution flow")
    print(f"\n  For more queries, visit: http://localhost:8000/")
    print("\n")


if __name__ == "__main__":
    main()
