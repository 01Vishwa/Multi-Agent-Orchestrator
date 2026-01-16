"""
ShipStream Models - Logistics & Delivery
Database: DB_ShipStream
Tables: Shipments, Warehouses, TrackingEvents
Dependency: Links to ShopCore via OrderID
"""
import uuid
from django.db import models
from apps.core.models import BaseModel


class Warehouse(BaseModel):
    """
    Distribution warehouse/hub for shipments.
    """
    REGION_CHOICES = [
        ('north', 'North'),
        ('south', 'South'),
        ('east', 'East'),
        ('west', 'West'),
        ('central', 'Central'),
    ]
    
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, help_text="City or address of warehouse")
    manager_name = models.CharField(max_length=255)
    region = models.CharField(max_length=20, choices=REGION_CHOICES, default='central')
    capacity = models.PositiveIntegerField(default=1000, help_text="Max items capacity")
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    
    class Meta:
        db_table = 'shipstream_warehouses'
        verbose_name = 'Warehouse'
        verbose_name_plural = 'Warehouses'
    
    def __str__(self):
        return f"{self.name} ({self.location})"


class Shipment(BaseModel):
    """
    Shipment for an order - links to ShopCore's Order via order_id.
    """
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('at_hub', 'At Hub'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('failed', 'Delivery Failed'),
        ('returned', 'Returned'),
    ]
    
    # Foreign key to ShopCore Order (stored as UUID, not Django FK for cross-app reference)
    order_id = models.UUIDField(help_text="Reference to ShopCore Order")
    tracking_number = models.CharField(max_length=50, unique=True)
    estimated_arrival = models.DateTimeField()
    actual_arrival = models.DateTimeField(blank=True, null=True)
    current_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='created')
    carrier = models.CharField(max_length=100, default='OmniShip')
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    
    # Current location tracking
    current_warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='current_shipments'
    )
    
    class Meta:
        db_table = 'shipstream_shipments'
        verbose_name = 'Shipment'
        verbose_name_plural = 'Shipments'
    
    def __str__(self):
        return f"Shipment {self.tracking_number} - {self.current_status}"
    
    def save(self, *args, **kwargs):
        # Auto-generate tracking number if not set
        if not self.tracking_number:
            self.tracking_number = f"OMN{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)


class TrackingEvent(BaseModel):
    """
    Individual tracking events for a shipment's journey.
    """
    EVENT_TYPES = [
        ('pickup', 'Package Picked Up'),
        ('arrival', 'Arrived at Facility'),
        ('departure', 'Departed Facility'),
        ('in_transit', 'In Transit'),
        ('customs', 'Customs Processing'),
        ('out_delivery', 'Out for Delivery'),
        ('delivered', 'Package Delivered'),
        ('exception', 'Delivery Exception'),
        ('returned', 'Package Returned'),
    ]
    
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='tracking_events')
    warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='tracking_events'
    )
    timestamp = models.DateTimeField()
    status_update = models.CharField(max_length=50, choices=EVENT_TYPES)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = 'shipstream_tracking_events'
        verbose_name = 'Tracking Event'
        verbose_name_plural = 'Tracking Events'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.shipment.tracking_number} - {self.status_update} at {self.timestamp}"
