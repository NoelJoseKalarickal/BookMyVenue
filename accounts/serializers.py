from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Customer
        fields = [
            "username",
            "email",
            "password",
            "name",
            "date_of_birth",
            "phone_number",
            "address_line_1",
            "address_line_2",
        ]