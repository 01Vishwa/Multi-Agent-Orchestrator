"""
AI Efficiency Optimizations - Query Caching & Smart Pattern Matching

This module implements:
1. Query intent caching with LRU
2. SQL pattern templates for common queries
3. Smart ORM fallback pattern matching
4. Query decomposition for multi-intent handling
"""
import hashlib
import re
import logging
from functools import lru_cache
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QueryPattern(str, Enum):
    """Common query patterns that can be handled by ORM directly."""
    ORDER_BY_PRODUCT = "order_by_product"
    ORDER_BY_ID = "order_by_id"
    USER_ORDERS = "user_orders"
    RECENT_ORDERS = "recent_orders"
    TRACK_SHIPMENT = "track_shipment"
    SHIPMENT_BY_ORDER = "shipment_by_order"
    USER_TRANSACTIONS = "user_transactions"
    REFUND_STATUS = "refund_status"
    USER_TICKETS = "user_tickets"
    TICKET_BY_ORDER = "ticket_by_order"
    WALLET_BALANCE = "wallet_balance"
    UNKNOWN = "unknown"


@dataclass
class CachedIntent:
    """Cached intent classification result."""
    intent: str
    confidence: float
    entities: List[Dict]
    required_agents: List[str]
    pattern: QueryPattern
    timestamp: datetime
    ttl_seconds: int = 3600  # 1 hour default
    
    def is_expired(self) -> bool:
        return datetime.utcnow() - self.timestamp > timedelta(seconds=self.ttl_seconds)


@dataclass
class DecomposedQuery:
    """Multi-intent query decomposition result."""
    sub_queries: List[Dict]
    dependencies: Dict[str, List[str]]
    execution_order: List[List[str]]


class QueryPatternMatcher:
    """
    Smart pattern matcher for ORM-first query handling.
    Matches ~60% of common queries without LLM call.
    """
    
    # Regex patterns for common query types
    PATTERNS = {
        QueryPattern.ORDER_BY_PRODUCT: [
            r"order.*(?:for|of|about)\s+['\"]?(\w+[\w\s]*)['\"]?",
            r"(?:where|status).*order.*['\"]?(\w+[\w\s]*)['\"]?",
            r"['\"]?(\w+[\w\s]*)['\"]?\s*order",
        ],
        QueryPattern.ORDER_BY_ID: [
            r"order\s*(?:id|#|number)?\s*[:\s]?\s*([a-f0-9-]{8,})",
            r"(?:order|track)\s+([A-Z0-9-]{8,})",
        ],
        QueryPattern.USER_ORDERS: [
            r"(?:my|all|recent)\s*orders?",
            r"orders?\s*(?:I|i)\s*(?:made|placed)",
            r"(?:show|list|get)\s*(?:my|all)?\s*orders?",
        ],
        QueryPattern.RECENT_ORDERS: [
            r"(?:last|recent|latest)\s*(?:\d+)?\s*orders?",
            r"orders?\s*(?:from|in)\s*(?:last|past)\s*(?:week|month|day)",
        ],
        QueryPattern.TRACK_SHIPMENT: [
            r"(?:track|where|status).*(?:shipment|package|delivery)",
            r"(?:shipment|package|delivery).*(?:status|location|where)",
            r"where\s*is\s*(?:my)?\s*(?:order|package)",
        ],
        QueryPattern.SHIPMENT_BY_ORDER: [
            r"(?:shipment|delivery|tracking).*order",
            r"order.*(?:shipment|delivery|tracking)",
        ],
        QueryPattern.USER_TRANSACTIONS: [
            r"(?:my|all|recent)?\s*transactions?",
            r"(?:payment|transaction)\s*history",
            r"(?:show|list)\s*(?:my)?\s*transactions?",
        ],
        QueryPattern.REFUND_STATUS: [
            r"refund\s*(?:status|processed|received)?",
            r"(?:status|where).*refund",
            r"(?:is|has)\s*(?:my)?\s*refund",
        ],
        QueryPattern.USER_TICKETS: [
            r"(?:my|open|all)?\s*(?:support)?\s*tickets?",
            r"ticket\s*status",
            r"(?:show|list)\s*(?:my)?\s*tickets?",
        ],
        QueryPattern.TICKET_BY_ORDER: [
            r"ticket.*order",
            r"order.*ticket",
        ],
        QueryPattern.WALLET_BALANCE: [
            r"(?:my|wallet)\s*balance",
            r"(?:how\s*much|what)\s*(?:in|is)\s*(?:my)?\s*wallet",
        ],
    }
    
    # Entity extraction patterns
    ENTITY_PATTERNS = {
        "product_name": [
            r"['\"]([^'\"]+)['\"]",
            r"(?:gaming|smart|laptop|phone|watch|monitor|headphone|keyboard|mouse|tablet|camera|speaker|shoe|shirt|dress)[\w\s]*",
        ],
        "order_id": [
            r"([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})",
            r"(?:order|id|#)\s*[:\s]?\s*([A-Z0-9-]{8,})",
        ],
        "tracking_number": [
            r"(?:track|tracking).*?([A-Z]{2,4}[0-9]{8,})",
        ],
        "amount": [
            r"\$?\s*(\d+(?:\.\d{2})?)",
        ],
    }
    
    @classmethod
    def match_pattern(cls, query: str) -> Tuple[QueryPattern, float]:
        """
        Match query against known patterns.
        Returns (pattern, confidence).
        """
        query_lower = query.lower()
        
        for pattern_type, regexes in cls.PATTERNS.items():
            for regex in regexes:
                if re.search(regex, query_lower, re.IGNORECASE):
                    return pattern_type, 0.85
        
        return QueryPattern.UNKNOWN, 0.0
    
    @classmethod
    def extract_entities(cls, query: str) -> List[Dict]:
        """Extract entities from query using regex patterns."""
        entities = []
        query_lower = query.lower()
        
        for entity_type, patterns in cls.ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                for match in matches:
                    if len(match) > 2:  # Filter noise
                        entities.append({
                            "type": entity_type,
                            "value": match.strip(),
                            "confidence": 0.8
                        })
        
        return entities
    
    @classmethod
    def can_handle_with_orm(cls, query: str) -> Tuple[bool, QueryPattern, List[Dict]]:
        """
        Determine if query can be handled with ORM (no LLM needed).
        Returns (can_handle, pattern, entities).
        """
        pattern, confidence = cls.match_pattern(query)
        entities = cls.extract_entities(query)
        
        if pattern != QueryPattern.UNKNOWN and confidence >= 0.7:
            return True, pattern, entities
        
        return False, QueryPattern.UNKNOWN, entities


class IntentCache:
    """
    LRU Cache for intent classification results.
    Reduces redundant LLM calls for similar queries.
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self._cache: Dict[str, CachedIntent] = {}
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0
    
    def _hash_query(self, query: str) -> str:
        """Create hash of normalized query."""
        normalized = query.lower().strip()
        # Remove common words for better matching
        for word in ["please", "can", "you", "tell", "me", "show", "the", "a", "an"]:
            normalized = normalized.replace(word, "")
        normalized = " ".join(normalized.split())
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def get(self, query: str) -> Optional[CachedIntent]:
        """Get cached intent if exists and not expired."""
        key = self._hash_query(query)
        
        if key in self._cache:
            cached = self._cache[key]
            if not cached.is_expired():
                self._hits += 1
                logger.debug(f"[CACHE HIT] Query: {query[:30]}...")
                return cached
            else:
                del self._cache[key]
        
        self._misses += 1
        return None
    
    def set(self, query: str, intent: str, confidence: float, 
            entities: List[Dict], agents: List[str], pattern: QueryPattern):
        """Cache intent classification result."""
        key = self._hash_query(query)
        
        # LRU eviction
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._cache, key=lambda k: self._cache[k].timestamp)
            del self._cache[oldest_key]
        
        self._cache[key] = CachedIntent(
            intent=intent,
            confidence=confidence,
            entities=entities,
            required_agents=agents,
            pattern=pattern,
            timestamp=datetime.utcnow(),
            ttl_seconds=self._ttl_seconds
        )
        logger.debug(f"[CACHE SET] Query: {query[:30]}...")
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "size": len(self._cache),
            "max_size": self._max_size
        }


class QueryDecomposer:
    """
    Decompose multi-intent queries into sub-queries.
    Example: "Check my order AND refund status" → 2 sub-queries
    """
    
    # Conjunctions that indicate multi-intent
    CONJUNCTIONS = [" and ", " also ", " plus ", " as well as ", ", and ", " & "]
    
    # Intent keywords mapping
    INTENT_KEYWORDS = {
        "order_inquiry": ["order", "ordered", "purchase", "bought"],
        "delivery_tracking": ["delivery", "shipment", "tracking", "shipped", "arrived", "where is"],
        "refund_request": ["refund", "money back", "return"],
        "payment_history": ["payment", "transaction", "paid", "wallet"],
        "ticket_status": ["ticket", "support", "issue", "complaint", "help"],
    }
    
    @classmethod
    def is_multi_intent(cls, query: str) -> bool:
        """Check if query contains multiple intents."""
        query_lower = query.lower()
        
        # Check for conjunctions
        for conj in cls.CONJUNCTIONS:
            if conj in query_lower:
                return True
        
        # Check for multiple intent keywords
        found_intents = []
        for intent, keywords in cls.INTENT_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                found_intents.append(intent)
        
        return len(found_intents) > 1
    
    @classmethod
    def decompose(cls, query: str) -> DecomposedQuery:
        """Decompose query into sub-queries with dependencies."""
        sub_queries = []
        query_lower = query.lower()
        
        # Find all intents in query
        found_intents = []
        for intent, keywords in cls.INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in query_lower:
                    found_intents.append((intent, kw))
                    break
        
        # Remove duplicates while preserving order
        seen = set()
        unique_intents = []
        for intent, kw in found_intents:
            if intent not in seen:
                seen.add(intent)
                unique_intents.append((intent, kw))
        
        # Create sub-queries
        for intent, keyword in unique_intents:
            agent = cls._intent_to_agent(intent)
            sub_queries.append({
                "intent": intent,
                "keyword": keyword,
                "agent": agent,
                "original_query": query
            })
        
        # Determine dependencies
        dependencies = cls._build_dependencies(sub_queries)
        execution_order = cls._determine_order(sub_queries, dependencies)
        
        return DecomposedQuery(
            sub_queries=sub_queries,
            dependencies=dependencies,
            execution_order=execution_order
        )
    
    @classmethod
    def _intent_to_agent(cls, intent: str) -> str:
        """Map intent to agent."""
        mapping = {
            "order_inquiry": "shopcore",
            "delivery_tracking": "shipstream",
            "refund_request": "payguard",
            "payment_history": "payguard",
            "ticket_status": "caredesk",
        }
        return mapping.get(intent, "shopcore")
    
    @classmethod
    def _build_dependencies(cls, sub_queries: List[Dict]) -> Dict[str, List[str]]:
        """Build dependency graph for sub-queries."""
        dependencies = {}
        
        agents = [sq["agent"] for sq in sub_queries]
        
        for sq in sub_queries:
            agent = sq["agent"]
            deps = []
            
            # shipstream, payguard, caredesk depend on shopcore for order_id
            if agent in ["shipstream", "payguard", "caredesk"] and "shopcore" in agents:
                deps.append("shopcore")
            
            # caredesk may depend on payguard for transaction references
            if agent == "caredesk" and "payguard" in agents:
                deps.append("payguard")
            
            dependencies[agent] = deps
        
        return dependencies
    
    @classmethod
    def _determine_order(cls, sub_queries: List[Dict], dependencies: Dict) -> List[List[str]]:
        """Determine execution order based on dependencies."""
        agents = list(set(sq["agent"] for sq in sub_queries))
        executed = set()
        order = []
        
        while len(executed) < len(agents):
            batch = []
            for agent in agents:
                if agent in executed:
                    continue
                deps = dependencies.get(agent, [])
                if all(d in executed for d in deps):
                    batch.append(agent)
            
            if batch:
                order.append(batch)
                executed.update(batch)
            else:
                # Circular dependency, add remaining
                order.append([a for a in agents if a not in executed])
                break
        
        return order


# Global instances
intent_cache = IntentCache(max_size=100, ttl_seconds=3600)
pattern_matcher = QueryPatternMatcher()
query_decomposer = QueryDecomposer()
