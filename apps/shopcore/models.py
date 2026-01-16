"""
ShopCore Models - E-commerce Platform
Database: DB_ShopCore
Tables: Users, Products, Orders
"""
from django.db import models
from apps.core.models import BaseModel


class User(BaseModel):
    """
    Customer/User account in the e-commerce platform.
    This is the central user entity referenced by other products.
    """
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    premium_status = models.BooleanField(default=False, help_text="Premium/VIP customer status")
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'shopcore_users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.name} ({self.email})"


class Product(BaseModel):
    """
    Product in the catalog.
    """
    CATEGORY_CHOICES = [
        ('electronics', 'Electronics'),
        ('clothing', 'Clothing'),
        ('home', 'Home & Kitchen'),
        ('books', 'Books'),
        ('sports', 'Sports & Outdoors'),
        ('beauty', 'Beauty & Personal Care'),
        ('toys', 'Toys & Games'),
        ('automotive', 'Automotive'),
        ('grocery', 'Grocery'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)
    
    class Meta:
        db_table = 'shopcore_products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
    
    def __str__(self):
        return f"{self.name} (${self.price})"


class Order(BaseModel):
    """
    Customer order for a product.
    This is a key entity that links to ShipStream and PayGuard.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    quantity = models.PositiveIntegerField(default=1)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'shopcore_orders'
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-order_date']
    
    def __str__(self):
        return f"Order {self.id} - {self.user.name} - {self.product.name}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate total if not set
        if not self.total_amount:
            self.total_amount = self.product.price * self.quantity
        super().save(*args, **kwargs)
