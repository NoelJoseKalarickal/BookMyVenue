from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from .serializers import (
    CustomerRegistrationSerializer,
    VenueOwnerRegistrationSerializer,
    OTPVerificationSerializer,
)
from .models import Customer, VenueOwner

class CustomerRegistrationView(APIView):

    def post(self, request):
        serializer = CustomerRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()

            return Response(
                {"message": "Customer registered successfully"},
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
                      

class VenueOwnerRegistrationView(APIView):

    def post(self, request):
        serializer = VenueOwnerRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()

            return Response(
                {"message": "Venue owner registered successfully"},
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class OTPVerificationView(APIView):

    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)

        if serializer.is_valid():

            email = serializer.validated_data["email"]
            otp = serializer.validated_data["otp"]

            cached_otp = cache.get(email)

            if cached_otp is None:
                return Response(
                    {"message": "OTP has expired or does not exist."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if otp != cached_otp:
                return Response(
                    {"message": "Invalid OTP."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            customer = Customer.objects.filter(user__email=email).first()

            if customer:
                customer.is_verified = True
                customer.save()

            else:
                venue_owner = VenueOwner.objects.filter(user__email=email).first()

                if venue_owner:
                    venue_owner.is_verified = True
                    venue_owner.save()

                else:
                    return Response(
                        {"message": "Account not found."},
                        status=status.HTTP_404_NOT_FOUND
                    )

            cache.delete(email)

            return Response(
                {"message": "OTP verified successfully."},
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )