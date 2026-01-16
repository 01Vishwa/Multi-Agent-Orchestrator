"""
Synthetic Data Generator for OmniLife Multi-Agent Orchestrator

This script generates realistic dummy data across all four product databases
with proper inter-database relationships.
"""
import os
import sys
import uuid
import random
from datetime import datetime, timedelta
from decimal import Decimal

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from faker import Faker
from apps.shopcore.models import User, Product, Order
from apps.shipstream.models import Warehouse, Shipment, TrackingEvent
from apps.payguard.models import Wallet, Transaction, PaymentMethod
from apps.caredesk.models import Ticket, TicketMessage, SatisfactionSurvey

fake = Faker()


def generate_users(count=50):
    """Generate dummy users."""
    print(f"Generating {count} users...")
    users = []
    
    for _ in range(count):
        user = User.objects.create(
            name=fake.name(),
            email=fake.unique.email(),
            premium_status=random.choice([True, False, False, False]),  # 25% premium
            phone=fake.phone_number()[:20],
            address=fake.address()
        )
        users.append(user)
    
    print(f"Created {len(users)} users")
    return users


def generate_products(count=100):
    """Generate dummy products."""
    print(f"Generating {count} products...")
    
    product_templates = [
        ('Gaming Monitor', 'electronics', 299.99, 599.99),
        ('Wireless Headphones', 'electronics', 49.99, 299.99),
        ('Laptop Stand', 'electronics', 29.99, 79.99),
        ('Smart Watch', 'electronics', 149.99, 499.99),
        ('USB-C Hub', 'electronics', 19.99, 89.99),
        ('Mechanical Keyboard', 'electronics', 79.99, 199.99),
        ('Gaming Mouse', 'electronics', 29.99, 129.99),
        ('Webcam HD', 'electronics', 49.99, 199.99),
        ('Bluetooth Speaker', 'electronics', 29.99, 149.99),
        ('Power Bank', 'electronics', 19.99, 79.99),
        ('Running Shoes', 'sports', 49.99, 199.99),
        ('Yoga Mat', 'sports', 19.99, 79.99),
        ('Dumbbell Set', 'sports', 29.99, 299.99),
        ('Fitness Tracker', 'sports', 49.99, 149.99),
        ('Cotton T-Shirt', 'clothing', 14.99, 49.99),
        ('Denim Jeans', 'clothing', 39.99, 129.99),
        ('Winter Jacket', 'clothing', 79.99, 299.99),
        ('Sneakers', 'clothing', 59.99, 189.99),
        ('Coffee Maker', 'home', 29.99, 199.99),
        ('Air Fryer', 'home', 49.99, 199.99),
        ('Vacuum Cleaner', 'home', 99.99, 399.99),
        ('Blender', 'home', 29.99, 149.99),
        ('Programming Book', 'books', 29.99, 79.99),
        ('Novel Bestseller', 'books', 9.99, 29.99),
        ('Educational Toys', 'toys', 19.99, 79.99),
        ('Board Game', 'toys', 24.99, 59.99),
    ]
    
    products = []
    
    for template in product_templates:
        name_base, category, min_price, max_price = template
        # Create variations
        for i in range(count // len(product_templates) + 1):
            if len(products) >= count:
                break
            
            variation = ['Pro', 'Lite', 'Plus', 'Max', 'Mini', 'Ultra', ''][random.randint(0, 6)]
            full_name = f"{name_base} {variation}".strip() if variation else name_base
            
            product = Product.objects.create(
                name=full_name,
                category=category,
                price=Decimal(str(round(random.uniform(min_price, max_price), 2))),
                description=fake.paragraph(nb_sentences=3),
                stock_quantity=random.randint(0, 500),
                sku=f"SKU-{uuid.uuid4().hex[:8].upper()}"
            )
            products.append(product)
    
    print(f"Created {len(products)} products")
    return products


def generate_orders(users, products, count=200):
    """Generate dummy orders."""
    print(f"Generating {count} orders...")
    orders = []
    
    statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded']
    status_weights = [5, 10, 10, 20, 40, 10, 5]  # Weighted probabilities
    
    for _ in range(count):
        user = random.choice(users)
        product = random.choice(products)
        quantity = random.randint(1, 3)
        order_status = random.choices(statuses, weights=status_weights)[0]
        
        # Order date in the last 30 days
        order_date = datetime.now() - timedelta(days=random.randint(0, 30))
        
        order = Order.objects.create(
            user=user,
            product=product,
            order_date=order_date,
            status=order_status,
            quantity=quantity,
            total_amount=product.price * quantity,
            shipping_address=user.address or fake.address()
        )
        orders.append(order)
    
    print(f"Created {len(orders)} orders")
    return orders


def generate_warehouses(count=10):
    """Generate dummy warehouses."""
    print(f"Generating {count} warehouses...")
    
    locations = [
        ('Mumbai Central Hub', 'Mumbai', 'west'),
        ('Delhi Distribution Center', 'Delhi', 'north'),
        ('Bangalore Tech Park', 'Bangalore', 'south'),
        ('Chennai Port Facility', 'Chennai', 'south'),
        ('Kolkata East Hub', 'Kolkata', 'east'),
        ('Hyderabad Logistics', 'Hyderabad', 'south'),
        ('Pune Distribution', 'Pune', 'west'),
        ('Ahmedabad Warehouse', 'Ahmedabad', 'west'),
        ('Jaipur Storage', 'Jaipur', 'north'),
        ('Lucknow Facility', 'Lucknow', 'north'),
    ]
    
    warehouses = []
    
    for name, location, region in locations[:count]:
        warehouse = Warehouse.objects.create(
            name=name,
            location=location,
            manager_name=fake.name(),
            region=region,
            capacity=random.randint(5000, 20000),
            contact_phone=fake.phone_number()[:20]
        )
        warehouses.append(warehouse)
    
    print(f"Created {len(warehouses)} warehouses")
    return warehouses


def generate_shipments(orders, warehouses):
    """Generate shipments for shipped/delivered orders."""
    print("Generating shipments...")
    shipments = []
    
    shipped_statuses = ['shipped', 'delivered']
    shipped_orders = [o for o in orders if o.status in shipped_statuses or random.random() > 0.3]
    
    shipment_statuses = {
        'pending': 'created',
        'confirmed': 'created',
        'processing': 'picked_up',
        'shipped': random.choice(['in_transit', 'at_hub', 'out_for_delivery']),
        'delivered': 'delivered',
        'cancelled': 'returned',
        'refunded': 'returned',
    }
    
    for order in shipped_orders[:150]:  # Limit shipments
        estimated_days = random.randint(2, 7)
        
        shipment = Shipment.objects.create(
            order_id=order.id,
            tracking_number=f"OMN{uuid.uuid4().hex[:10].upper()}",
            estimated_arrival=order.order_date + timedelta(days=estimated_days),
            actual_arrival=order.order_date + timedelta(days=estimated_days) if order.status == 'delivered' else None,
            current_status=shipment_statuses.get(order.status, 'in_transit'),
            carrier=random.choice(['OmniShip', 'FastDeliver', 'SpeedPost', 'QuickLogistics']),
            weight_kg=Decimal(str(round(random.uniform(0.5, 15.0), 2))),
            current_warehouse=random.choice(warehouses) if order.status != 'delivered' else None
        )
        shipments.append(shipment)
    
    print(f"Created {len(shipments)} shipments")
    return shipments


def generate_tracking_events(shipments, warehouses):
    """Generate tracking events for shipments."""
    print("Generating tracking events...")
    events = []
    
    event_flow = ['pickup', 'departure', 'in_transit', 'arrival', 'departure', 'in_transit', 'arrival', 'out_delivery', 'delivered']
    
    for shipment in shipments:
        # Number of events based on status
        if shipment.current_status == 'delivered':
            num_events = len(event_flow)
        elif shipment.current_status == 'created':
            num_events = 1
        else:
            num_events = random.randint(2, 6)
        
        base_time = shipment.created_at
        
        for i in range(min(num_events, len(event_flow))):
            event_type = event_flow[i]
            event_time = base_time + timedelta(hours=random.randint(2, 12) * (i + 1))
            
            event = TrackingEvent.objects.create(
                shipment=shipment,
                warehouse=random.choice(warehouses) if event_type in ['arrival', 'departure'] else None,
                timestamp=event_time,
                status_update=event_type,
                description=f"Package {event_type.replace('_', ' ')}",
                location=random.choice(warehouses).location if event_type != 'delivered' else shipment.current_warehouse.location if shipment.current_warehouse else 'Customer Address'
            )
            events.append(event)
    
    print(f"Created {len(events)} tracking events")
    return events


def generate_wallets(users):
    """Generate wallets for users."""
    print("Generating wallets...")
    wallets = []
    
    for user in users:
        wallet = Wallet.objects.create(
            user_id=user.id,
            balance=Decimal(str(round(random.uniform(0, 5000), 2))),
            currency='USD',
            is_active=True
        )
        wallets.append(wallet)
    
    print(f"Created {len(wallets)} wallets")
    return wallets


def generate_transactions(wallets, orders):
    """Generate transactions linked to orders."""
    print("Generating transactions...")
    transactions = []
    
    # Map orders to wallets via user
    user_wallet_map = {w.user_id: w for w in wallets}
    
    for order in orders:
        wallet = user_wallet_map.get(order.user.id)
        if not wallet:
            continue
        
        # Primary debit transaction for the order
        trans = Transaction.objects.create(
            wallet=wallet,
            order_id=order.id,
            amount=order.total_amount,
            transaction_type='debit',
            status='completed',
            description=f"Payment for order",
            reference_number=f"TXN{uuid.uuid4().hex[:12].upper()}",
            processed_at=order.order_date + timedelta(minutes=5)
        )
        transactions.append(trans)
        
        # Refund transaction for refunded orders
        if order.status == 'refunded':
            refund = Transaction.objects.create(
                wallet=wallet,
                order_id=order.id,
                amount=order.total_amount,
                transaction_type='refund',
                status='completed',
                description=f"Refund for order",
                reference_number=f"REF{uuid.uuid4().hex[:12].upper()}",
                processed_at=order.order_date + timedelta(days=random.randint(1, 5))
            )
            transactions.append(refund)
    
    print(f"Created {len(transactions)} transactions")
    return transactions


def generate_payment_methods(wallets):
    """Generate payment methods for wallets."""
    print("Generating payment methods...")
    methods = []
    
    providers = ['visa', 'mastercard', 'amex', 'paypal', 'upi']
    
    for wallet in wallets:
        num_methods = random.randint(1, 3)
        
        for i in range(num_methods):
            method = PaymentMethod.objects.create(
                wallet=wallet,
                provider=random.choice(providers),
                last_four_digits=str(random.randint(1000, 9999)),
                expiry_date=datetime.now().date() + timedelta(days=random.randint(30, 1000)),
                is_default=(i == 0),
                is_active=True,
                nickname=f"My {random.choice(['Primary', 'Backup', 'Work', 'Personal'])} Card"
            )
            methods.append(method)
    
    print(f"Created {len(methods)} payment methods")
    return methods


def generate_tickets(users, orders):
    """Generate support tickets."""
    print("Generating tickets...")
    tickets = []
    
    issue_types = ['order', 'delivery', 'payment', 'refund', 'product', 'general']
    issue_subjects = {
        'order': ['Order not received', 'Wrong item received', 'Order cancelled but charged'],
        'delivery': ['Package delayed', 'Tracking not updating', 'Delivery address change'],
        'payment': ['Double charged', 'Payment failed', 'Card declined'],
        'refund': ['Refund not processed', 'Partial refund received', 'Refund taking too long'],
        'product': ['Defective product', 'Missing parts', 'Product quality issue'],
        'general': ['Account issue', 'App not working', 'General inquiry'],
    }
    
    # Create tickets for ~30% of orders
    ticket_orders = random.sample(orders, min(len(orders) // 3, 60))
    
    for order in ticket_orders:
        issue_type = random.choice(issue_types)
        
        ticket = Ticket.objects.create(
            user_id=order.user.id,
            reference_id=order.id,
            reference_type='order',
            issue_type=issue_type,
            status=random.choice(['open', 'in_progress', 'resolved', 'closed']),
            priority=random.choice(['low', 'medium', 'high', 'urgent']),
            subject=random.choice(issue_subjects[issue_type]),
            description=fake.paragraph(nb_sentences=3),
            assigned_agent_id=uuid.uuid4() if random.random() > 0.3 else None,
            assigned_agent_name=fake.name() if random.random() > 0.3 else None,
        )
        tickets.append(ticket)
    
    print(f"Created {len(tickets)} tickets")
    return tickets


def generate_ticket_messages(tickets):
    """Generate messages for tickets."""
    print("Generating ticket messages...")
    messages = []
    
    for ticket in tickets:
        # Initial customer message
        msg1 = TicketMessage.objects.create(
            ticket=ticket,
            sender='user',
            sender_name='Customer',
            content=fake.paragraph(nb_sentences=2),
            is_internal=False
        )
        messages.append(msg1)
        
        # Agent response if ticket is not open
        if ticket.status != 'open' and ticket.assigned_agent_name:
            msg2 = TicketMessage.objects.create(
                ticket=ticket,
                sender='agent',
                sender_name=ticket.assigned_agent_name,
                content=fake.paragraph(nb_sentences=2),
                is_internal=False
            )
            messages.append(msg2)
            
            # Maybe a follow-up
            if random.random() > 0.5:
                msg3 = TicketMessage.objects.create(
                    ticket=ticket,
                    sender='user',
                    sender_name='Customer',
                    content=fake.paragraph(nb_sentences=1),
                    is_internal=False
                )
                messages.append(msg3)
    
    print(f"Created {len(messages)} ticket messages")
    return messages


def generate_surveys(tickets):
    """Generate satisfaction surveys for closed tickets."""
    print("Generating surveys...")
    surveys = []
    
    closed_tickets = [t for t in tickets if t.status in ['resolved', 'closed']]
    surveyed_tickets = random.sample(closed_tickets, min(len(closed_tickets), len(closed_tickets) // 2))
    
    for ticket in surveyed_tickets:
        survey = SatisfactionSurvey.objects.create(
            ticket=ticket,
            rating=random.choices([1, 2, 3, 4, 5], weights=[5, 10, 15, 30, 40])[0],
            comments=fake.paragraph(nb_sentences=1) if random.random() > 0.5 else None,
            would_recommend=random.choice([True, True, True, False])
        )
        surveys.append(survey)
    
    print(f"Created {len(surveys)} surveys")
    return surveys


def clear_all_data():
    """Clear all existing data."""
    print("Clearing existing data...")
    
    SatisfactionSurvey.objects.all().delete()
    TicketMessage.objects.all().delete()
    Ticket.objects.all().delete()
    PaymentMethod.objects.all().delete()
    Transaction.objects.all().delete()
    Wallet.objects.all().delete()
    TrackingEvent.objects.all().delete()
    Shipment.objects.all().delete()
    Warehouse.objects.all().delete()
    Order.objects.all().delete()
    Product.objects.all().delete()
    User.objects.all().delete()
    
    print("All data cleared")


def main():
    """Main function to generate all data."""
    print("\n" + "="*60)
    print("OmniLife Synthetic Data Generator")
    print("="*60 + "\n")
    
    # Clear existing data
    clear_all_data()
    
    # Generate data in order of dependencies
    users = generate_users(50)
    products = generate_products(100)
    orders = generate_orders(users, products, 200)
    
    warehouses = generate_warehouses(10)
    shipments = generate_shipments(orders, warehouses)
    tracking_events = generate_tracking_events(shipments, warehouses)
    
    wallets = generate_wallets(users)
    transactions = generate_transactions(wallets, orders)
    payment_methods = generate_payment_methods(wallets)
    
    tickets = generate_tickets(users, orders)
    ticket_messages = generate_ticket_messages(tickets)
    surveys = generate_surveys(tickets)
    
    print("\n" + "="*60)
    print("Data Generation Complete!")
    print("="*60)
    print(f"\nSummary:")
    print(f"  - Users: {len(users)}")
    print(f"  - Products: {len(products)}")
    print(f"  - Orders: {len(orders)}")
    print(f"  - Warehouses: {len(warehouses)}")
    print(f"  - Shipments: {len(shipments)}")
    print(f"  - Tracking Events: {len(tracking_events)}")
    print(f"  - Wallets: {len(wallets)}")
    print(f"  - Transactions: {len(transactions)}")
    print(f"  - Payment Methods: {len(payment_methods)}")
    print(f"  - Tickets: {len(tickets)}")
    print(f"  - Ticket Messages: {len(ticket_messages)}")
    print(f"  - Surveys: {len(surveys)}")
    print()


if __name__ == '__main__':
    main()
