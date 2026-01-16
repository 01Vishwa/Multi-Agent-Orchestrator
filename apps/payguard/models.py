"""
PayGuard Models - FinTech & Transactions
Database: DB_PayGuard
Tables: Wallets, Transactions, PaymentMethods
Dependency: Links to ShopCore via UserID and OrderID
"""
from django.db import models
from apps.core.models import BaseModel


class Wallet(BaseModel):
    """
    Digital wallet for a user - links to ShopCore's User via user_id.
    """
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('INR', 'Indian Rupee'),
        ('JPY', 'Japanese Yen'),
    ]
    
    # Foreign key to ShopCore User (stored as UUID for cross-app reference)
    user_id = models.UUIDField(unique=True, help_text="Reference to ShopCore User")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    is_active = models.BooleanField(default=True)
    last_transaction_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'payguard_wallets'
        verbose_name = 'Wallet'
        verbose_name_plural = 'Wallets'
    
    def __str__(self):
        return f"Wallet {self.id} - {self.balance} {self.currency}"


class Transaction(BaseModel):
    """
    Financial transaction - debit, credit, or refund.
    Links to ShopCore's Order via order_id.
    """
    TYPE_CHOICES = [
        ('debit', 'Debit'),
        ('credit', 'Credit'),
        ('refund', 'Refund'),
        ('cashback', 'Cashback'),
        ('fee', 'Fee'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    order_id = models.UUIDField(blank=True, null=True, help_text="Reference to ShopCore Order (if applicable)")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.CharField(max_length=255, blank=True, null=True)
    reference_number = models.CharField(max_length=50, unique=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'payguard_transactions'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} {self.wallet.currency}"


class PaymentMethod(BaseModel):
    """
    Saved payment methods for a wallet.
    """
    PROVIDER_CHOICES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('paypal', 'PayPal'),
        ('upi', 'UPI'),
        ('bank_transfer', 'Bank Transfer'),
        ('wallet', 'Digital Wallet'),
    ]
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='payment_methods')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    last_four_digits = models.CharField(max_length=4, blank=True, null=True, help_text="Last 4 digits of card")
    expiry_date = models.DateField(blank=True, null=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    nickname = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        db_table = 'payguard_payment_methods'
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
    
    def __str__(self):
        return f"{self.provider} ****{self.last_four_digits or 'XXXX'}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default per wallet
        if self.is_default:
            PaymentMethod.objects.filter(wallet=self.wallet, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
