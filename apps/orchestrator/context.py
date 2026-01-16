"""
Context Window Optimization - Memory Management for Multi-Agent System

This module implements strategies to optimize context windows:
1. Selective memory retention (only keep relevant context)
2. Database-first retrieval (avoid storing large datasets in memory)
3. Compressed context summaries
4. Session-based memory with TTL
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import OrderedDict

logger = logging.getLogger(__name__)


@dataclass
class ContextItem:
    """Single item in the context window."""
    key: str
    value: Any
    timestamp: datetime
    token_estimate: int
    priority: int = 1  # 1=high, 2=medium, 3=low
    source: str = "user"  # user, agent, system
    

@dataclass
class ConversationSummary:
    """Compressed summary of a conversation."""
    user_intent: str
    entities_mentioned: List[str]
    agents_consulted: List[str]
    key_findings: List[str]
    timestamp: datetime


class ContextWindowManager:
    """
    Manages the context window for the orchestrator to optimize token usage.
    
    Strategy:
    1. Keep only last N messages in full
    2. Summarize older messages
    3. Store entity references (IDs) not full data
    4. Retrieve from database when needed
    """
    
    # Token limits (configurable)
    MAX_CONTEXT_TOKENS = 4000  # Reserve tokens for context
    MAX_FULL_MESSAGES = 5      # Keep last N messages in full
    MAX_ENTITIES = 20          # Maximum entity references to keep
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[Dict] = []
        self.entities: OrderedDict = OrderedDict()  # LRU cache
        self.summaries: List[ConversationSummary] = []
        self.current_token_count = 0
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """
        Add a message to the context, applying optimization rules.
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        # Estimate tokens (rough: 1 token ≈ 4 chars)
        token_estimate = len(content) // 4
        message["token_estimate"] = token_estimate
        
        self.messages.append(message)
        self.current_token_count += token_estimate
        self.last_activity = datetime.utcnow()
        
        # Apply optimization if over limit
        self._optimize_context()
    
    def add_entity(self, entity_type: str, entity_id: str, summary: str = None):
        """
        Add an entity reference to context (ID only, not full data).
        Data is retrieved from database when needed.
        """
        key = f"{entity_type}:{entity_id}"
        
        self.entities[key] = {
            "type": entity_type,
            "id": entity_id,
            "summary": summary,  # Brief summary for context
            "added_at": datetime.utcnow().isoformat()
        }
        
        # LRU eviction
        if len(self.entities) > self.MAX_ENTITIES:
            self.entities.popitem(last=False)
    
    def get_entity(self, entity_type: str, entity_id: str) -> Optional[Dict]:
        """
        Get entity data - retrieves from database if not in memory.
        This is the key optimization: we store IDs, not data.
        """
        key = f"{entity_type}:{entity_id}"
        
        if key in self.entities:
            # Move to end (most recently used)
            self.entities.move_to_end(key)
            
            # The entity reference is in context, now fetch fresh data
            return self._fetch_from_database(entity_type, entity_id)
        
        return None
    
    def _fetch_from_database(self, entity_type: str, entity_id: str) -> Optional[Dict]:
        """
        Fetch entity data from database.
        This saves tokens by not keeping full data in context.
        """
        try:
            if entity_type == "order":
                from apps.shopcore.models import Order
                order = Order.objects.select_related('user', 'product').get(id=entity_id)
                return {
                    "order_id": str(order.id),
                    "product": order.product.name,
                    "status": order.status,
                    "amount": str(order.total_amount)
                }
            elif entity_type == "shipment":
                from apps.shipstream.models import Shipment
                shipment = Shipment.objects.get(id=entity_id)
                return {
                    "shipment_id": str(shipment.id),
                    "tracking": shipment.tracking_number,
                    "status": shipment.current_status
                }
            elif entity_type == "transaction":
                from apps.payguard.models import Transaction
                trans = Transaction.objects.get(id=entity_id)
                return {
                    "transaction_id": str(trans.id),
                    "type": trans.transaction_type,
                    "amount": str(trans.amount),
                    "status": trans.status
                }
            elif entity_type == "ticket":
                from apps.caredesk.models import Ticket
                ticket = Ticket.objects.get(id=entity_id)
                return {
                    "ticket_id": str(ticket.id),
                    "subject": ticket.subject,
                    "status": ticket.status
                }
        except Exception as e:
            logger.error(f"Error fetching {entity_type} {entity_id}: {e}")
        
        return None
    
    def _optimize_context(self):
        """
        Optimize context when over token limit.
        Strategy: Summarize old messages, keep recent ones in full.
        """
        if self.current_token_count <= self.MAX_CONTEXT_TOKENS:
            return
        
        logger.info(f"Optimizing context: {self.current_token_count} tokens")
        
        # Keep last N messages in full
        if len(self.messages) > self.MAX_FULL_MESSAGES:
            old_messages = self.messages[:-self.MAX_FULL_MESSAGES]
            self.messages = self.messages[-self.MAX_FULL_MESSAGES:]
            
            # Create summary of old messages
            summary = self._create_summary(old_messages)
            self.summaries.append(summary)
            
            # Recalculate token count
            self.current_token_count = sum(
                m.get("token_estimate", 0) for m in self.messages
            )
        
        logger.info(f"Context optimized: {self.current_token_count} tokens")
    
    def _create_summary(self, messages: List[Dict]) -> ConversationSummary:
        """
        Create a compressed summary of messages.
        This drastically reduces token usage for older context.
        """
        user_messages = [m["content"] for m in messages if m["role"] == "user"]
        agent_messages = [m["metadata"].get("agents", []) for m in messages if m["role"] == "assistant"]
        
        # Extract key information
        entities = []
        agents = []
        for msg in messages:
            if "metadata" in msg:
                entities.extend(msg["metadata"].get("entities", []))
                agents.extend(msg["metadata"].get("agents", []))
        
        return ConversationSummary(
            user_intent=user_messages[0][:100] if user_messages else "",
            entities_mentioned=list(set(entities))[:10],
            agents_consulted=list(set(a for sublist in agent_messages for a in (sublist if isinstance(sublist, list) else []))),
            key_findings=["Conversation summarized for token optimization"],
            timestamp=datetime.utcnow()
        )
    
    def get_context_for_llm(self) -> Dict:
        """
        Get optimized context ready for LLM consumption.
        Returns minimal data needed for continuation.
        """
        context = {
            "session_id": self.session_id,
            "messages": self.messages[-self.MAX_FULL_MESSAGES:],
            "entity_references": list(self.entities.values())[-10:],
            "summaries": [
                {
                    "intent": s.user_intent,
                    "entities": s.entities_mentioned,
                    "agents": s.agents_consulted
                }
                for s in self.summaries[-3:]  # Last 3 summaries
            ],
            "token_estimate": self.current_token_count
        }
        
        return context
    
    def get_relevant_context(self, query: str) -> Dict:
        """
        Get only context relevant to the current query.
        Further reduces tokens by filtering.
        """
        # Keywords to match
        keywords = set(query.lower().split())
        
        # Filter messages to only relevant ones
        relevant_messages = []
        for msg in self.messages:
            msg_words = set(msg["content"].lower().split())
            if keywords & msg_words:  # Intersection
                relevant_messages.append(msg)
        
        return {
            "messages": relevant_messages[-3:],  # Last 3 relevant
            "entities": list(self.entities.values())[-5:]
        }


class SessionMemoryStore:
    """
    Store for managing multiple session contexts.
    Implements TTL-based cleanup.
    """
    
    SESSION_TTL = timedelta(hours=24)
    MAX_SESSIONS = 1000
    
    def __init__(self):
        self._sessions: Dict[str, ContextWindowManager] = {}
    
    def get_or_create(self, session_id: str) -> ContextWindowManager:
        """Get existing session or create new one."""
        self._cleanup_expired()
        
        if session_id not in self._sessions:
            self._sessions[session_id] = ContextWindowManager(session_id)
        
        return self._sessions[session_id]
    
    def _cleanup_expired(self):
        """Remove expired sessions to free memory."""
        now = datetime.utcnow()
        expired = [
            sid for sid, ctx in self._sessions.items()
            if now - ctx.last_activity > self.SESSION_TTL
        ]
        
        for sid in expired:
            del self._sessions[sid]
            logger.debug(f"Cleaned up expired session: {sid}")
        
        # Also limit total sessions
        if len(self._sessions) > self.MAX_SESSIONS:
            # Remove oldest sessions
            sorted_sessions = sorted(
                self._sessions.items(),
                key=lambda x: x[1].last_activity
            )
            for sid, _ in sorted_sessions[:len(self._sessions) - self.MAX_SESSIONS]:
                del self._sessions[sid]


# Global session store
session_store = SessionMemoryStore()
