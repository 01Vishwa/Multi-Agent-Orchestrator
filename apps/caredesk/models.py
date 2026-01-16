"""
CareDesk Models - Customer Support
Database: DB_CareDesk
Tables: Tickets, TicketMessages, SatisfactionSurveys
Dependency: Links to all other DBs via ReferenceID and UserID
"""
import uuid
from django.db import models
from apps.core.models import BaseModel


class Ticket(BaseModel):
    """
    Support ticket - can reference orders, transactions, or other entities.
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('waiting_customer', 'Waiting on Customer'),
        ('waiting_internal', 'Waiting on Internal Team'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    ISSUE_TYPE_CHOICES = [
        ('order', 'Order Issue'),
        ('delivery', 'Delivery Issue'),
        ('payment', 'Payment Issue'),
        ('refund', 'Refund Request'),
        ('product', 'Product Issue'),
        ('account', 'Account Issue'),
        ('general', 'General Inquiry'),
        ('complaint', 'Complaint'),
        ('feedback', 'Feedback'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    REFERENCE_TYPE_CHOICES = [
        ('order', 'Order'),
        ('transaction', 'Transaction'),
        ('shipment', 'Shipment'),
        ('product', 'Product'),
        ('other', 'Other'),
    ]
    
    # Foreign key to ShopCore User
    user_id = models.UUIDField(help_text="Reference to ShopCore User")
    
    # Flexible reference to any entity (Order, Transaction, etc.)
    reference_id = models.UUIDField(blank=True, null=True, help_text="Reference to related entity (Order, Transaction, etc.)")
    reference_type = models.CharField(max_length=20, choices=REFERENCE_TYPE_CHOICES, blank=True, null=True)
    
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPE_CHOICES, default='general')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    subject = models.CharField(max_length=255)
    description = models.TextField()
    
    # Assignment
    assigned_agent_id = models.UUIDField(blank=True, null=True, help_text="Support agent assigned to ticket")
    assigned_agent_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Timestamps
    first_response_at = models.DateTimeField(blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'caredesk_tickets'
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Ticket {self.id} - {self.subject[:50]}"


class TicketMessage(BaseModel):
    """
    Individual messages/replies within a ticket thread.
    """
    SENDER_CHOICES = [
        ('user', 'Customer'),
        ('agent', 'Support Agent'),
        ('system', 'System'),
    ]
    
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    sender_name = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField()
    is_internal = models.BooleanField(default=False, help_text="Internal notes not visible to customer")
    
    class Meta:
        db_table = 'caredesk_ticket_messages'
        verbose_name = 'Ticket Message'
        verbose_name_plural = 'Ticket Messages'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender} on Ticket {self.ticket_id}"


class SatisfactionSurvey(BaseModel):
    """
    Customer satisfaction survey after ticket resolution.
    """
    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name='survey')
    rating = models.PositiveSmallIntegerField(help_text="Rating from 1-5")
    comments = models.TextField(blank=True, null=True)
    would_recommend = models.BooleanField(blank=True, null=True)
    completed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'caredesk_satisfaction_surveys'
        verbose_name = 'Satisfaction Survey'
        verbose_name_plural = 'Satisfaction Surveys'
    
    def __str__(self):
        return f"Survey for Ticket {self.ticket_id} - Rating: {self.rating}/5"
    
    def save(self, *args, **kwargs):
        # Validate rating is 1-5
        if self.rating < 1 or self.rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        super().save(*args, **kwargs)
