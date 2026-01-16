"""
MCP Protocol Implementation - Model Context Protocol for Safe API Interaction

This module implements:
1. Strict Function Calling protocol adherence
2. Tool schemas with validation
3. Safe interaction with external APIs
4. Error handling and retry logic
"""
import logging
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Categories for tool/function organization."""
    DATABASE_READ = "database_read"
    DATABASE_WRITE = "database_write"  # Not implemented - read-only system
    EXTERNAL_API = "external_api"
    INTERNAL_API = "internal_api"
    UTILITY = "utility"


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str  # string, integer, boolean, array, object
    description: str
    required: bool = False
    default: Any = None
    enum: List[str] = None  # For restricted values


@dataclass
class ToolDefinition:
    """
    Complete tool definition following OpenAI Function Calling format.
    Compatible with MCP protocol.
    """
    name: str
    description: str
    parameters: List[ToolParameter]
    category: ToolCategory
    returns: str  # Description of return value
    
    def to_openai_schema(self) -> Dict:
        """Convert to OpenAI function calling schema."""
        properties = {}
        required = []
        
        for param in self.parameters:
            param_schema = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                param_schema["enum"] = param.enum
            if param.default is not None:
                param_schema["default"] = param.default
            
            properties[param.name] = param_schema
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
    
    def to_mcp_schema(self) -> Dict:
        """Convert to MCP (Model Context Protocol) schema."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": {
                    param.name: {
                        "type": param.type,
                        "description": param.description,
                        **({"enum": param.enum} if param.enum else {}),
                        **({"default": param.default} if param.default is not None else {})
                    }
                    for param in self.parameters
                },
                "required": [p.name for p in self.parameters if p.required]
            }
        }


class MCPToolRegistry:
    """
    Registry for MCP-compliant tools.
    Provides safe access to internal APIs.
    """
    
    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}
        self._register_default_tools()
    
    def register(self, definition: ToolDefinition, handler: Callable):
        """Register a tool with its handler."""
        self._tools[definition.name] = definition
        self._handlers[definition.name] = handler
        logger.info(f"Registered MCP tool: {definition.name}")
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get tool definition by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[ToolDefinition]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def get_openai_tools(self) -> List[Dict]:
        """Get all tools in OpenAI function calling format."""
        return [tool.to_openai_schema() for tool in self._tools.values()]
    
    def get_mcp_tools(self) -> List[Dict]:
        """Get all tools in MCP format."""
        return [tool.to_mcp_schema() for tool in self._tools.values()]
    
    def execute(self, tool_name: str, arguments: Dict) -> Dict:
        """
        Execute a tool with validation.
        Follows MCP protocol for safe execution.
        """
        if tool_name not in self._tools:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "data": None
            }
        
        tool = self._tools[tool_name]
        handler = self._handlers[tool_name]
        
        # Validate required parameters
        for param in tool.parameters:
            if param.required and param.name not in arguments:
                return {
                    "success": False,
                    "error": f"Missing required parameter: {param.name}",
                    "data": None
                }
        
        # Apply defaults
        for param in tool.parameters:
            if param.name not in arguments and param.default is not None:
                arguments[param.name] = param.default
        
        try:
            result = handler(**arguments)
            return {
                "success": True,
                "error": None,
                "data": result
            }
        except Exception as e:
            logger.error(f"Tool execution error [{tool_name}]: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": None
            }
    
    def _register_default_tools(self):
        """Register default OmniLife tools."""
        
        # === ShopCore Tools ===
        self.register(
            ToolDefinition(
                name="shopcore_find_orders",
                description="Find orders in the ShopCore database. Use this when you need order information, status, or customer order history.",
                parameters=[
                    ToolParameter("product_name", "string", "Product name to search for (partial match)", required=False),
                    ToolParameter("order_id", "string", "Specific order ID to find", required=False),
                    ToolParameter("user_id", "string", "Filter by user ID", required=False),
                    ToolParameter("status", "string", "Filter by order status", required=False, enum=["pending", "confirmed", "processing", "shipped", "delivered", "cancelled", "refunded"]),
                    ToolParameter("limit", "integer", "Maximum results (default: 5)", required=False, default=5)
                ],
                category=ToolCategory.DATABASE_READ,
                returns="List of orders with order_id, product, status, amount, date"
            ),
            handler=self._handler_shopcore_find_orders
        )
        
        self.register(
            ToolDefinition(
                name="shopcore_find_products",
                description="Search products in the catalog. Use for product inquiries.",
                parameters=[
                    ToolParameter("name", "string", "Product name (partial match)", required=False),
                    ToolParameter("category", "string", "Product category", required=False),
                    ToolParameter("limit", "integer", "Maximum results", required=False, default=5)
                ],
                category=ToolCategory.DATABASE_READ,
                returns="List of products with id, name, category, price, stock"
            ),
            handler=self._handler_shopcore_find_products
        )
        
        # === ShipStream Tools ===
        self.register(
            ToolDefinition(
                name="shipstream_track_shipment",
                description="Track a shipment by order ID or tracking number. Use for delivery status inquiries.",
                parameters=[
                    ToolParameter("order_id", "string", "Order ID to find shipment for", required=False),
                    ToolParameter("tracking_number", "string", "Tracking number", required=False),
                ],
                category=ToolCategory.DATABASE_READ,
                returns="Shipment details with status, location, tracking events"
            ),
            handler=self._handler_shipstream_track
        )
        
        # === PayGuard Tools ===
        self.register(
            ToolDefinition(
                name="payguard_check_transactions",
                description="Check transaction history including payments and refunds.",
                parameters=[
                    ToolParameter("user_id", "string", "User ID for wallet lookup", required=False),
                    ToolParameter("order_id", "string", "Order ID to find related transactions", required=False),
                    ToolParameter("transaction_type", "string", "Filter by type", required=False, enum=["payment", "refund", "credit"]),
                    ToolParameter("limit", "integer", "Maximum results", required=False, default=5)
                ],
                category=ToolCategory.DATABASE_READ,
                returns="List of transactions with type, amount, status, date"
            ),
            handler=self._handler_payguard_transactions
        )
        
        # === CareDesk Tools ===
        self.register(
            ToolDefinition(
                name="caredesk_find_tickets",
                description="Find support tickets for a user. Use for ticket status inquiries.",
                parameters=[
                    ToolParameter("user_id", "string", "User ID", required=False),
                    ToolParameter("order_id", "string", "Related order ID", required=False),
                    ToolParameter("status", "string", "Ticket status filter", required=False, enum=["open", "in_progress", "resolved", "closed"]),
                ],
                category=ToolCategory.DATABASE_READ,
                returns="List of tickets with subject, status, priority, assigned agent"
            ),
            handler=self._handler_caredesk_tickets
        )
    
    # === Tool Handlers ===
    
    def _handler_shopcore_find_orders(self, **kwargs) -> List[Dict]:
        from apps.shopcore.models import Order
        
        orders = Order.objects.select_related('user', 'product').all()
        
        if kwargs.get('product_name'):
            orders = orders.filter(product__name__icontains=kwargs['product_name'])
        if kwargs.get('order_id'):
            orders = orders.filter(id=kwargs['order_id'])
        if kwargs.get('user_id'):
            orders = orders.filter(user_id=kwargs['user_id'])
        if kwargs.get('status'):
            orders = orders.filter(status=kwargs['status'])
        
        limit = kwargs.get('limit', 5)
        return [
            {
                'order_id': str(o.id),
                'product_name': o.product.name,
                'user_name': o.user.name,
                'status': o.status,
                'amount': str(o.total_amount),
                'date': o.order_date.isoformat()
            }
            for o in orders[:limit]
        ]
    
    def _handler_shopcore_find_products(self, **kwargs) -> List[Dict]:
        from apps.shopcore.models import Product
        
        products = Product.objects.all()
        
        if kwargs.get('name'):
            products = products.filter(name__icontains=kwargs['name'])
        if kwargs.get('category'):
            products = products.filter(category=kwargs['category'])
        
        limit = kwargs.get('limit', 5)
        return [
            {
                'product_id': str(p.id),
                'name': p.name,
                'category': p.category,
                'price': str(p.price),
                'stock': p.stock_quantity
            }
            for p in products[:limit]
        ]
    
    def _handler_shipstream_track(self, **kwargs) -> List[Dict]:
        from apps.shipstream.models import Shipment, TrackingEvent
        
        shipments = Shipment.objects.select_related('current_warehouse').all()
        
        if kwargs.get('order_id'):
            shipments = shipments.filter(order_id=kwargs['order_id'])
        if kwargs.get('tracking_number'):
            shipments = shipments.filter(tracking_number=kwargs['tracking_number'])
        
        results = []
        for s in shipments[:5]:
            events = TrackingEvent.objects.filter(shipment=s).order_by('-timestamp')[:5]
            results.append({
                'shipment_id': str(s.id),
                'tracking_number': s.tracking_number,
                'status': s.current_status,
                'location': s.current_warehouse.location if s.current_warehouse else 'In Transit',
                'estimated_arrival': s.estimated_arrival.isoformat() if s.estimated_arrival else None,
                'events': [
                    {'status': e.status_update, 'time': e.timestamp.isoformat()}
                    for e in events[:3]
                ]
            })
        return results
    
    def _handler_payguard_transactions(self, **kwargs) -> List[Dict]:
        from apps.payguard.models import Transaction
        
        transactions = Transaction.objects.select_related('wallet').order_by('-created_at')
        
        if kwargs.get('user_id'):
            transactions = transactions.filter(wallet__user_id=kwargs['user_id'])
        if kwargs.get('order_id'):
            transactions = transactions.filter(order_id=kwargs['order_id'])
        if kwargs.get('transaction_type'):
            transactions = transactions.filter(transaction_type=kwargs['transaction_type'])
        
        limit = kwargs.get('limit', 5)
        return [
            {
                'transaction_id': str(t.id),
                'type': t.transaction_type,
                'status': t.status,
                'amount': str(t.amount),
                'date': t.created_at.isoformat(),
                'reference': t.reference_number
            }
            for t in transactions[:limit]
        ]
    
    def _handler_caredesk_tickets(self, **kwargs) -> List[Dict]:
        from apps.caredesk.models import Ticket
        
        tickets = Ticket.objects.all().order_by('-created_at')
        
        if kwargs.get('user_id'):
            tickets = tickets.filter(user_id=kwargs['user_id'])
        if kwargs.get('order_id'):
            tickets = tickets.filter(reference_id=kwargs['order_id'], reference_type='order')
        if kwargs.get('status'):
            tickets = tickets.filter(status=kwargs['status'])
        
        return [
            {
                'ticket_id': str(t.id),
                'subject': t.subject,
                'status': t.status,
                'priority': t.priority,
                'issue_type': t.issue_type,
                'assigned_to': t.assigned_agent_name or 'Unassigned',
                'created': t.created_at.isoformat()
            }
            for t in tickets[:5]
        ]


# Global registry instance
mcp_registry = MCPToolRegistry()


def get_available_tools_for_llm() -> List[Dict]:
    """Get tools in OpenAI function calling format for LLM."""
    return mcp_registry.get_openai_tools()


def execute_tool(tool_name: str, arguments: Dict) -> Dict:
    """Execute a registered tool safely."""
    return mcp_registry.execute(tool_name, arguments)
