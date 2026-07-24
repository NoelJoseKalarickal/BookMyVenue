from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer, VenueOwner
import random
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from django.core.mail import send_mail


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

        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError(
                {"username": "This username is already taken."})
    

        if Customer.objects.filter(user__email=email).exists():
            raise serializers.ValidationError(
                {"email": "A customer account with this email already exists."})
                                             
        otp = str(random.randint(100000, 999999))

        cache.set(email, otp, timeout=300)
        
        send_mail(
            subject="BookMyVenue OTP Verification",
            message=f"Your OTP is: {otp}\n\nThis OTP is valid for 5 minutes.",
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
            )


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
        if User.objects.filter(username=username).exists():
            raise serializers.ValidationError(
                {"username": "This username is already taken."})
    
        if VenueOwner.objects.filter(user__email=email).exists():
            raise serializers.ValidationError(
                  {"email": "A venue owner account with this email already exists."})
    

        otp = str(random.randint(100000, 999999))

        cache.set(
            email,
            otp,
            timeout=300
        )

        send_mail(
            subject="BookMyVenue OTP Verification",
            message=f"Your OTP is: {otp}\n\nThis OTP is valid for 5 minutes.",
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )

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
class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)