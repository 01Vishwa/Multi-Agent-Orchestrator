"""
PayGuard Database Schema Definition
Used by the PayGuard agent for text-to-SQL generation
"""

PAYGUARD_SCHEMA = {
    "database": "DB_PayGuard",
    "description": "FinTech database for wallet management, payment processing, and refund tracking",
    "tables": [
        {
            "name": "payguard_wallets",
            "description": "Digital wallets linked to user accounts",
            "columns": [
                {"name": "id", "type": "UUID", "primary_key": True, "description": "Unique wallet identifier (WalletID)"},
                {"name": "user_id", "type": "UUID", "foreign_key": "shopcore_users.id", "unique": True, "description": "Reference to ShopCore user (one wallet per user)"},
                {"name": "balance", "type": "DECIMAL(12,2)", "description": "Current wallet balance"},
                {"name": "currency", "type": "VARCHAR(3)", "description": "Currency code: USD, EUR, GBP, INR, JPY"},
                {"name": "is_active", "type": "BOOLEAN", "description": "Whether wallet is active"},
                {"name": "last_transaction_at", "type": "TIMESTAMP", "nullable": True, "description": "Last transaction timestamp"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "Wallet creation timestamp"},
                {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"},
            ]
        },
        {
            "name": "payguard_transactions",
            "description": "Financial transactions including payments and refunds",
            "columns": [
                {"name": "id", "type": "UUID", "primary_key": True, "description": "Unique transaction identifier (TransactionID)"},
                {"name": "wallet_id", "type": "UUID", "foreign_key": "payguard_wallets.id", "description": "Reference to wallet"},
                {"name": "order_id", "type": "UUID", "foreign_key": "shopcore_orders.id", "nullable": True, "description": "Reference to ShopCore order (if applicable)"},
                {"name": "amount", "type": "DECIMAL(12,2)", "description": "Transaction amount"},
                {"name": "transaction_type", "type": "VARCHAR(20)", "description": "Type: debit, credit, refund, cashback, fee"},
                {"name": "status", "type": "VARCHAR(20)", "description": "Status: pending, processing, completed, failed, reversed"},
                {"name": "description", "type": "VARCHAR(255)", "nullable": True, "description": "Transaction description"},
                {"name": "reference_number", "type": "VARCHAR(50)", "unique": True, "description": "Unique reference number"},
                {"name": "processed_at", "type": "TIMESTAMP", "nullable": True, "description": "When transaction was processed"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "Transaction creation timestamp"},
                {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"},
            ]
        },
        {
            "name": "payguard_payment_methods",
            "description": "Saved payment methods (cards, UPI, etc.)",
            "columns": [
                {"name": "id", "type": "UUID", "primary_key": True, "description": "Unique payment method identifier (MethodID)"},
                {"name": "wallet_id", "type": "UUID", "foreign_key": "payguard_wallets.id", "description": "Reference to wallet"},
                {"name": "provider", "type": "VARCHAR(20)", "description": "Provider: visa, mastercard, amex, paypal, upi, bank_transfer, wallet"},
                {"name": "last_four_digits", "type": "VARCHAR(4)", "nullable": True, "description": "Last 4 digits of card number"},
                {"name": "expiry_date", "type": "DATE", "nullable": True, "description": "Card expiry date"},
                {"name": "is_default", "type": "BOOLEAN", "description": "Whether this is the default payment method"},
                {"name": "is_active", "type": "BOOLEAN", "description": "Whether method is active"},
                {"name": "nickname", "type": "VARCHAR(50)", "nullable": True, "description": "User-defined name for method"},
                {"name": "created_at", "type": "TIMESTAMP", "description": "Record creation timestamp"},
                {"name": "updated_at", "type": "TIMESTAMP", "description": "Last update timestamp"},
            ]
        }
    ],
    "relationships": [
        "payguard_wallets.user_id -> shopcore_users.id (One wallet per user)",
        "payguard_transactions.wallet_id -> payguard_wallets.id (Many transactions per wallet)",
        "payguard_transactions.order_id -> shopcore_orders.id (Payment for order)",
        "payguard_payment_methods.wallet_id -> payguard_wallets.id (Many methods per wallet)"
    ],
    "common_queries": [
        "Get wallet balance for a user",
        "Find refund status for an order",
        "List all transactions for a user",
        "Check if refund was processed",
        "Get payment methods for a wallet",
        "Find transactions by order ID"
    ]
}


def get_schema_prompt() -> str:
    """Generate a prompt-friendly schema description."""
    lines = [
        f"# {PAYGUARD_SCHEMA['database']} Schema",
        f"{PAYGUARD_SCHEMA['description']}\n",
        "## Tables\n"
    ]
    
    for table in PAYGUARD_SCHEMA['tables']:
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
