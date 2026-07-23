from django.contrib import admin

# Register your models here.
from .models import Customer, VenueOwner, EmailOTP

admin.site.register(Customer)
admin.site.register(VenueOwner)
admin.site.register(EmailOTP)