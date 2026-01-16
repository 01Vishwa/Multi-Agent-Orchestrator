"""
ShopCore Database Schema Definition
Used by the ShopCore agent for text-to-SQL generation
"""

SHOPCORE_SCHEMA = {
    "database": "DB_ShopCore",
    "description": "E-commerce platform database containing user accounts, product catalog, and orders",
    "tables": [
        {
            "name": "shopcore_users",
            "description": "Customer accounts and profiles",
            "columns": [
                {"name": "id", "type": "UUID", "primary_key": True, "description": "Unique user identifier"},
                {"name": "name", "type": "VARCHAR(255)", "description": "Customer full name"},
                {"name": "email", "type": "VARCHAR(255)", "unique": True, "description": "Customer email address"},
                {"name": "premium_status", "type": "BOOLEAN", "description": "True if premium/VIP customer"},
                {"name": "phone", "type": "VARCHAR(20)", "nullable": True, "description": "Contact phone number"},
                {"name": "address", "type": "TEXT", "nullable": True, "description": "Shipping address"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "Account creation date"},
                {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"},
            ]
        },
        {
            "name": "shopcore_products",
            "description": "Product catalog",
            "columns": [
                {"name": "id", "type": "UUID", "primary_key": True, "description": "Unique product identifier"},
                {"name": "name", "type": "VARCHAR(255)", "description": "Product name"},
                {"name": "category", "type": "VARCHAR(50)", "description": "Product category (electronics, clothing, home, etc.)"},
                {"name": "price", "type": "DECIMAL(10,2)", "description": "Product price in USD"},
                {"name": "description", "type": "TEXT", "nullable": True, "description": "Product description"},
                {"name": "stock_quantity", "type": "INTEGER", "description": "Available stock quantity"},
                {"name": "sku", "type": "VARCHAR(50)", "unique": True, "nullable": True, "description": "Stock keeping unit"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "Product listing date"},
                {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"},
            ]
        },
        {
            "name": "shopcore_orders",
            "description": "Customer orders",
            "columns": [
                {"name": "id", "type": "UUID", "primary_key": True, "description": "Unique order identifier (OrderID)"},
                {"name": "user_id", "type": "UUID", "foreign_key": "shopcore_users.id", "description": "Customer who placed the order"},
                {"name": "product_id", "type": "UUID", "foreign_key": "shopcore_products.id", "description": "Product ordered"},
                {"name": "order_date", "type": "TIMESTAMP", "description": "Date and time order was placed"},
                {"name": "status", "type": "VARCHAR(20)", "description": "Order status: pending, confirmed, processing, shipped, delivered, cancelled, refunded"},
                {"name": "quantity", "type": "INTEGER", "description": "Number of items ordered"},
                {"name": "total_amount", "type": "DECIMAL(12,2)", "description": "Total order amount in USD"},
                {"name": "shipping_address", "type": "TEXT", "nullable": True, "description": "Delivery address"},
                {"name": "notes", "type": "TEXT", "nullable": True, "description": "Order notes"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "Record creation timestamp"},
                {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"},
            ]
        }
    ],
    "relationships": [
        "shopcore_orders.user_id -> shopcore_users.id (Many orders to one user)",
        "shopcore_orders.product_id -> shopcore_products.id (Many orders to one product)"
    ],
    "common_queries": [
        "Find orders by user email or name",
        "Get order details including product name and price",
        "Find orders by product name or category",
        "Check order status",
        "List all premium customers",
        "Find recent orders within a date range"
    ]
}


def get_schema_prompt() -> str:
    """Generate a prompt-friendly schema description."""
    lines = [
        f"# {SHOPCORE_SCHEMA['database']} Schema",
        f"{SHOPCORE_SCHEMA['description']}\n",
        "## Tables\n"
    ]
    
    for table in SHOPCORE_SCHEMA['tables']:
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
