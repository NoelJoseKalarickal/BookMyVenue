from django.contrib import admin

# Register your models here.
from .models import Customer, VenueOwner

admin.site.register(Customer)
admin.site.register(VenueOwner)