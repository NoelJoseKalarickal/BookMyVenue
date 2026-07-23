from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer, VenueOwner, EmailOTP
import random
from datetime import timedelta
from django.utils import timezone


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

    def create(self, validated_data):
        username = validated_data.pop("username")
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        otp = str(random.randint(100000, 999999))

        EmailOTP.objects.create(
            email=email,
            otp=otp,
            expires_at=timezone.now() + timedelta(minutes=5))
             
        print(f"OTP for {email}: {otp}")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        customer = Customer.objects.create(
            user=user,
            **validated_data
        )

        return customer
    



class VenueOwnerRegistrationSerializer(serializers.ModelSerializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    class Meta:
        model = VenueOwner
        fields = [
            "username",
            "email",
            "password",
            "name",
            "date_of_birth",
            "phone_number",
            "address_line_1",
            "address_line_2",
            "bank_details",
        ]

    def create(self, validated_data):
        username = validated_data.pop("username")
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        otp = str(random.randint(100000, 999999))


        EmailOTP.objects.create(
            email=email,
            otp=otp,
            expires_at=timezone.now() + timedelta(minutes=5))
             
        print(f"OTP for {email}: {otp}")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        venue_owner = VenueOwner.objects.create(
            user=user,
            **validated_data
        )

        return venue_owner