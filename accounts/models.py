from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address_line_1 = models.CharField(max_length=100)
    address_line_2 = models.CharField(max_length=100, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class VenueOwner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address_line_1 = models.CharField(max_length=100)
    address_line_2 = models.CharField(max_length=100, blank=True, null=True)
    bank_details = models.TextField()
    is_verified = models.BooleanField(default=False)

    # Razorpay Route
    razorpay_account_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    razorpay_stakeholder_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    razorpay_product_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.name