"""
ShipStream Database Schema Definition
Used by the ShipStream agent for text-to-SQL generation
"""

SHIPSTREAM_SCHEMA = {
    "database": "DB_ShipStream",
    "description": "Logistics and delivery database for tracking shipments, warehouses, and delivery events",
    "tables": [
        {
            "name": "shipstream_warehouses",
            "description": "Distribution warehouses and hubs",
            "columns": [
                {"name": "id", "type": "UUID", "primary_key": True, "description": "Unique warehouse identifier"},
                {"name": "name", "type": "VARCHAR(255)", "description": "Warehouse name"},
                {"name": "location", "type": "VARCHAR(255)", "description": "City or address of warehouse"},
                {"name": "manager_name", "type": "VARCHAR(255)", "description": "Warehouse manager's name"},
                {"name": "region", "type": "VARCHAR(20)", "description": "Region: north, south, east, west, central"},
                {"name": "capacity", "type": "INTEGER", "description": "Maximum item capacity"},
                {"name": "contact_phone", "type": "VARCHAR(20)", "nullable": True, "description": "Contact phone"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "Record creation timestamp"},
                {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"},
            ]
        },
        {
            "name": "shipstream_shipments",
            "description": "Shipments linked to orders from ShopCore",
            "columns": [
                {"name": "id", "type": "UUID", "primary_key": True, "description": "Unique shipment identifier (ShipmentID)"},
                {"name": "order_id", "type": "UUID", "foreign_key": "shopcore_orders.id", "description": "Reference to ShopCore order"},
                {"name": "tracking_number", "type": "VARCHAR(50)", "unique": True, "description": "Unique tracking number"},
                {"name": "estimated_arrival", "type": "TIMESTAMP", "description": "Estimated delivery date/time"},
                {"name": "actual_arrival", "type": "TIMESTAMP", "nullable": True, "description": "Actual delivery date/time"},
                {"name": "current_status", "type": "VARCHAR(30)", "description": "Status: created, picked_up, in_transit, at_hub, out_for_delivery, delivered, failed, returned"},
                {"name": "carrier", "type": "VARCHAR(100)", "description": "Shipping carrier name"},
                {"name": "weight_kg", "type": "DECIMAL(6,2)", "nullable": True, "description": "Package weight in kg"},
                {"name": "current_warehouse_id", "type": "UUID", "foreign_key": "shipstream_warehouses.id", "nullable": True, "description": "Current warehouse location"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "Shipment creation timestamp"},
                {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"},
            ]
        },
        {
            "name": "shipstream_tracking_events",
            "description": "Individual tracking events showing shipment journey",
            "columns": [
                {"name": "id", "type": "UUID", "primary_key": True, "description": "Unique event identifier"},
                {"name": "shipment_id", "type": "UUID", "foreign_key": "shipstream_shipments.id", "description": "Reference to shipment"},
                {"name": "warehouse_id", "type": "UUID", "foreign_key": "shipstream_warehouses.id", "nullable": True, "description": "Warehouse where event occurred"},
                {"name": "timestamp", "type": "TIMESTAMP", "description": "When the event occurred"},
                {"name": "status_update", "type": "VARCHAR(50)", "description": "Event type: pickup, arrival, departure, in_transit, customs, out_delivery, delivered, exception, returned"},
                {"name": "description", "type": "TEXT", "nullable": True, "description": "Detailed event description"},
                {"name": "location", "type": "VARCHAR(255)", "nullable": True, "description": "Location where event occurred"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "Record creation timestamp"},
                {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"},
            ]
        }
    ],
    "relationships": [
        "shipstream_shipments.order_id -> shopcore_orders.id (One shipment per order)",
        "shipstream_shipments.current_warehouse_id -> shipstream_warehouses.id (Current location)",
        "shipstream_tracking_events.shipment_id -> shipstream_shipments.id (Many events per shipment)",
        "shipstream_tracking_events.warehouse_id -> shipstream_warehouses.id (Event location)"
    ],
    "common_queries": [
        "Get shipment status by order ID",
        "Find tracking events for a shipment",
        "Get current location of a package",
        "Find shipments at a specific warehouse",
        "List delayed shipments (past estimated arrival)",
        "Get shipment history by tracking number"
    ]
}


def get_schema_prompt() -> str:
    """Generate a prompt-friendly schema description."""
    lines = [
        f"# {SHIPSTREAM_SCHEMA['database']} Schema",
        f"{SHIPSTREAM_SCHEMA['description']}\n",
        "## Tables\n"
    ]
    
    for table in SHIPSTREAM_SCHEMA['tables']:
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
