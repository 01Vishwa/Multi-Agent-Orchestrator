"""
Reasoning Chain - Chain-of-Thought Logging for Super Agent

This module implements:
1. Reasoning chain capture (WHY each decision was made)
2. Confidence scoring at each step
3. Detailed thought process logging
4. Error recovery with retry logic
"""
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ReasoningStep(str, Enum):
    """Types of reasoning steps in the thought process."""
    QUERY_RECEIVED = "query_received"
    PATTERN_MATCH = "pattern_match"
    INTENT_CLASSIFICATION = "intent_classification"
    ENTITY_EXTRACTION = "entity_extraction"
    AGENT_SELECTION = "agent_selection"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    EXECUTION_PLANNING = "execution_planning"
    AGENT_EXECUTION = "agent_execution"
    DATA_EXTRACTION = "data_extraction"
    RESPONSE_SYNTHESIS = "response_synthesis"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class ThoughtStep:
    """Single step in the reasoning chain."""
    step_type: ReasoningStep
    thought: str
    decision: str
    confidence: float
    timestamp: float
    duration_ms: float = 0.0
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "step": self.step_type.value,
            "thought": self.thought,
            "decision": self.decision,
            "confidence": self.confidence,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata
        }


class ReasoningChain:
    """
    Captures the step-by-step thought process of the Super Agent.
    Provides transparency for demo logs and debugging.
    """
    
    def __init__(self, query: str, session_id: str):
        self.query = query
        self.session_id = session_id
        self.steps: List[ThoughtStep] = []
        self.start_time = time.time()
        self.current_step_start: float = 0.0
    
    def start_step(self):
        """Mark start of a step for timing."""
        self.current_step_start = time.time()
    
    def add_step(
        self,
        step_type: ReasoningStep,
        thought: str,
        decision: str,
        confidence: float = 1.0,
        metadata: Dict = None
    ):
        """Add a reasoning step to the chain."""
        duration = (time.time() - self.current_step_start) * 1000 if self.current_step_start else 0
        
        step = ThoughtStep(
            step_type=step_type,
            thought=thought,
            decision=decision,
            confidence=confidence,
            timestamp=time.time() - self.start_time,
            duration_ms=duration,
            metadata=metadata or {}
        )
        
        self.steps.append(step)
        
        # Log for visibility
        logger.info(f"[REASONING] {step_type.value}: {thought} → {decision} ({confidence:.0%})")
        
        return step
    
    def get_chain(self) -> List[Dict]:
        """Get full reasoning chain as list of dicts."""
        return [step.to_dict() for step in self.steps]
    
    def get_summary(self) -> str:
        """Get human-readable summary of reasoning."""
        lines = [
            f"\n{'='*60}",
            f"REASONING CHAIN - Query: {self.query[:50]}...",
            f"{'='*60}"
        ]
        
        for i, step in enumerate(self.steps, 1):
            lines.append(f"\n{i}. [{step.step_type.value.upper()}]")
            lines.append(f"   💭 Thought: {step.thought}")
            lines.append(f"   ✅ Decision: {step.decision}")
            lines.append(f"   📊 Confidence: {step.confidence:.0%} | Time: {step.duration_ms:.0f}ms")
        
        total_time = (time.time() - self.start_time) * 1000
        lines.append(f"\n{'='*60}")
        lines.append(f"TOTAL TIME: {total_time:.0f}ms")
        lines.append(f"{'='*60}\n")
        
        return "\n".join(lines)
    
    def get_final_confidence(self) -> float:
        """Get overall confidence (product of all step confidences)."""
        if not self.steps:
            return 0.0
        
        confidence = 1.0
        for step in self.steps:
            confidence *= step.confidence
        
        return confidence


class ErrorRecovery:
    """
    Error recovery with intelligent retry logic.
    Modifies prompts and approaches based on failure patterns.
    """
    
    MAX_RETRIES = 2
    
    # Error patterns and recovery strategies
    RECOVERY_STRATEGIES = {
        "sql_syntax": {
            "pattern": ["syntax error", "no such column", "no such table"],
            "strategy": "Use ORM fallback",
            "action": "orm_fallback"
        },
        "empty_result": {
            "pattern": ["no results", "empty", "not found"],
            "strategy": "Broaden search criteria",
            "action": "broaden_search"
        },
        "timeout": {
            "pattern": ["timeout", "timed out", "too long"],
            "strategy": "Simplify query",
            "action": "simplify"
        },
        "llm_error": {
            "pattern": ["rate limit", "api error", "connection"],
            "strategy": "Use cached or ORM fallback",
            "action": "cache_or_orm"
        }
    }
    
    @classmethod
    def should_retry(cls, error: str, attempt: int) -> bool:
        """Determine if we should retry based on error and attempt count."""
        return attempt < cls.MAX_RETRIES
    
    @classmethod
    def get_recovery_action(cls, error: str) -> Dict:
        """Determine best recovery action based on error pattern."""
        error_lower = error.lower()
        
        for error_type, config in cls.RECOVERY_STRATEGIES.items():
            for pattern in config["pattern"]:
                if pattern in error_lower:
                    return {
                        "error_type": error_type,
                        "strategy": config["strategy"],
                        "action": config["action"]
                    }
        
        return {
            "error_type": "unknown",
            "strategy": "Use ORM fallback",
            "action": "orm_fallback"
        }
    
    @classmethod
    def execute_with_recovery(
        cls,
        agent,
        query: str,
        context: Dict,
        entities: List,
        reasoning: ReasoningChain
    ) -> Dict:
        """
        Execute agent with error recovery.
        Tries multiple approaches if initial fails.
        """
        attempts = []
        last_error = None
        
        for attempt in range(cls.MAX_RETRIES + 1):
            try:
                reasoning.start_step()
                
                if attempt == 0:
                    # First attempt: normal execution
                    result = agent.execute(query, context, entities)
                else:
                    # Recovery attempt
                    recovery = cls.get_recovery_action(last_error)
                    
                    reasoning.add_step(
                        ReasoningStep.ERROR_RECOVERY,
                        f"Attempt {attempt} failed: {last_error[:50]}",
                        f"Recovery: {recovery['strategy']}",
                        confidence=0.7,
                        metadata={"attempt": attempt, "recovery": recovery}
                    )
                    
                    if recovery["action"] == "orm_fallback":
                        result = agent._orm_fallback(query, context, entities)
                    elif recovery["action"] == "broaden_search":
                        # Remove specific filters
                        modified_context = {k: v for k, v in context.items() if k not in ["status", "date"]}
                        result = agent._orm_fallback(query, modified_context, entities)
                    else:
                        result = agent._orm_fallback(query, context, entities)
                
                if result.get("success"):
                    return result
                
                last_error = result.get("error", "Unknown error")
                attempts.append({
                    "attempt": attempt + 1,
                    "error": last_error
                })
                
            except Exception as e:
                last_error = str(e)
                attempts.append({
                    "attempt": attempt + 1,
                    "exception": str(e)
                })
        
        # All attempts failed
        return {
            "success": False,
            "error": f"All {cls.MAX_RETRIES + 1} attempts failed. Last error: {last_error}",
            "data": [],
            "attempts": attempts
        }


class ConfidenceScorer:
    """
    Calculate confidence scores for various decisions.
    """
    
    @staticmethod
    def intent_confidence(
        pattern_match_conf: float,
        entity_extraction_conf: float,
        llm_conf: float = 0.0
    ) -> float:
        """Combined intent confidence from multiple sources."""
        if llm_conf > 0:
            # If LLM was used, weight it higher
            return (pattern_match_conf * 0.3 + entity_extraction_conf * 0.3 + llm_conf * 0.4)
        else:
            # Pattern matching only
            return (pattern_match_conf * 0.6 + entity_extraction_conf * 0.4)
    
    @staticmethod
    def agent_selection_confidence(
        intent_conf: float,
        dependency_clarity: float = 1.0
    ) -> float:
        """Confidence in agent selection."""
        return intent_conf * dependency_clarity
    
    @staticmethod
    def result_confidence(
        sql_executed: bool,
        row_count: int,
        expected_fields_present: bool
    ) -> float:
        """Confidence in result quality."""
        base = 1.0 if sql_executed else 0.5
        
        if row_count == 0:
            base *= 0.6  # Lower confidence for empty results
        elif row_count > 10:
            base *= 0.9  # Slightly lower for large results (might be too broad)
        
        if not expected_fields_present:
            base *= 0.7
        
        return min(base, 1.0)


# Factory function to create reasoning chain
def create_reasoning_chain(query: str, session_id: str) -> ReasoningChain:
    """Create a new reasoning chain for a query."""
    return ReasoningChain(query, session_id)
