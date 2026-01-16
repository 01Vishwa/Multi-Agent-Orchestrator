"""
CareDesk Database Schema Definition
Used by the CareDesk agent for text-to-SQL generation
"""

CAREDESK_SCHEMA = {
    "database": "DB_CareDesk",
    "description": "Customer support database for tickets, conversations, and satisfaction tracking",
    "tables": [
        {
            "name": "caredesk_tickets",
            "description": "Support tickets from customers",
            "columns": [
                {"name": "id", "type": "UUID", "primary_key": True, "description": "Unique ticket identifier (TicketID)"},
                {"name": "user_id", "type": "UUID", "foreign_key": "shopcore_users.id", "description": "Reference to ShopCore user"},
                {"name": "reference_id", "type": "UUID", "nullable": True, "description": "Reference to related entity (OrderID, TransactionID, ShipmentID, etc.)"},
                {"name": "reference_type", "type": "VARCHAR(20)", "nullable": True, "description": "Type of reference: order, transaction, shipment, product, other"},
                {"name": "issue_type", "type": "VARCHAR(20)", "description": "Issue type: order, delivery, payment, refund, product, account, general, complaint, feedback"},
                {"name": "status", "type": "VARCHAR(20)", "description": "Status: open, in_progress, waiting_customer, waiting_internal, resolved, closed"},
                {"name": "priority", "type": "VARCHAR(10)", "description": "Priority: low, medium, high, urgent"},
                {"name": "subject", "type": "VARCHAR(255)", "description": "Ticket subject/title"},
                {"name": "description", "type": "TEXT", "description": "Detailed description of the issue"},
                {"name": "assigned_agent_id", "type": "UUID", "nullable": True, "description": "Support agent assigned to ticket"},
                {"name": "assigned_agent_name", "type": "VARCHAR(255)", "nullable": True, "description": "Name of assigned agent"},
                {"name": "first_response_at", "type": "TIMESTAMP", "nullable": True, "description": "When first response was sent"},
                {"name": "resolved_at", "type": "TIMESTAMP", "nullable": True, "description": "When ticket was resolved"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "Ticket creation timestamp"},
                {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"},
            ]
        },
        {
            "name": "caredesk_ticket_messages",
            "description": "Messages and replies within tickets",
            "columns": [
                {"name": "id", "type": "UUID", "primary_key": True, "description": "Unique message identifier (MessageID)"},
                {"name": "ticket_id", "type": "UUID", "foreign_key": "caredesk_tickets.id", "description": "Reference to ticket"},
                {"name": "sender", "type": "VARCHAR(10)", "description": "Sender type: user (customer), agent (support), system"},
                {"name": "sender_name", "type": "VARCHAR(255)", "nullable": True, "description": "Name of the sender"},
                {"name": "content", "type": "TEXT", "description": "Message content"},
                {"name": "is_internal", "type": "BOOLEAN", "description": "True if internal note (not visible to customer)"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "Message timestamp"},
                {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"},
            ]
        },
        {
            "name": "caredesk_satisfaction_surveys",
            "description": "Customer satisfaction surveys after ticket resolution",
            "columns": [
                {"name": "id", "type": "UUID", "primary_key": True, "description": "Unique survey identifier (SurveyID)"},
                {"name": "ticket_id", "type": "UUID", "foreign_key": "caredesk_tickets.id", "unique": True, "description": "Reference to ticket (one survey per ticket)"},
                {"name": "rating", "type": "INTEGER", "description": "Customer rating from 1 to 5"},
                {"name": "comments", "type": "TEXT", "nullable": True, "description": "Customer comments/feedback"},
                {"name": "would_recommend", "type": "BOOLEAN", "nullable": True, "description": "Would customer recommend the service"},
                {"name": "completed_at", "type": "TIMESTAMP", "description": "When survey was completed"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "Record creation timestamp"},
                {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"},
            ]
        }
    ],
    "relationships": [
        "caredesk_tickets.user_id -> shopcore_users.id (Tickets by user)",
        "caredesk_tickets.reference_id -> (shopcore_orders.id OR payguard_transactions.id OR shipstream_shipments.id) based on reference_type",
        "caredesk_ticket_messages.ticket_id -> caredesk_tickets.id (Many messages per ticket)",
        "caredesk_satisfaction_surveys.ticket_id -> caredesk_tickets.id (One survey per ticket)"
    ],
    "common_queries": [
        "Find ticket status by user",
        "Check if ticket is assigned to an agent",
        "Get ticket history for an order",
        "Find open tickets for a user",
        "Get satisfaction rating for resolved tickets",
        "List messages in a ticket thread"
    ]
}


def get_schema_prompt() -> str:
    """Generate a prompt-friendly schema description."""
    lines = [
        f"# {CAREDESK_SCHEMA['database']} Schema",
        f"{CAREDESK_SCHEMA['description']}\n",
        "## Tables\n"
    ]
    
    for table in CAREDESK_SCHEMA['tables']:
        lines.append(f"### {table['name']}")
        lines.append(f"{table['description']}\n")
        lines.append("| Column | Type | Description |")
        lines.append("|--------|------|-------------|")
        
        for col in table['columns']:
            constraints = []
            if col.get('primary_key'):
                constraints.append("PK")
            if col.get('foreign_key'):
                constraints.append(f"FK→{col['foreign_key']}")
            if col.get('unique'):
                constraints.append("UNIQUE")
            
            constraint_str = f" [{', '.join(constraints)}]" if constraints else ""
            lines.append(f"| {col['name']} | {col['type']}{constraint_str} | {col['description']} |")
        
        lines.append("")
    
    return '\n'.join(lines)
