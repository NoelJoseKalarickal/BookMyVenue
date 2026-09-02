from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from django.core.cache import cache

from .serializers import (
    CustomerRegistrationSerializer,
    VenueOwnerRegistrationSerializer,
    OTPVerificationSerializer,
)

from .models import Customer, VenueOwner

from payments.route_service import (
    create_linked_account,
    create_stakeholder,
    request_route_product_configuration,
    update_route_product_configuration,
)


class CustomerRegistrationView(APIView):

    def post(self, request):
        serializer = CustomerRegistrationSerializer(
            data=request.data
        )

        if serializer.is_valid():
            user = serializer.save()

            return Response(
                {
                    "message": "Customer registered successfully.",
                    "user_id": user.id,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class VenueOwnerRegistrationView(APIView):

    def post(self, request):
        serializer = VenueOwnerRegistrationSerializer(
            data=request.data
        )

        if serializer.is_valid():
            user = serializer.save()

            return Response(
                {
                    "message": "Venue owner registered successfully.",
                    "user_id": user.id,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class VerifyOTPView(APIView):

    def post(self, request):
        serializer = OTPVerificationSerializer(
            data=request.data
        )

        if serializer.is_valid():
            return Response(
                {
                    "message": "OTP verified successfully."
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class CreateRazorpayLinkedAccountView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        venue_owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if venue_owner is None:
            return Response(
                {
                    "message":
                    "Only venue owners can create "
                    "a Razorpay linked account."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if venue_owner.razorpay_account_id:
            return Response(
                {
                    "message":
                    "Razorpay linked account already exists.",
                    "razorpay_account_id":
                    venue_owner.razorpay_account_id,
                },
                status=status.HTTP_200_OK,
            )

        if not venue_owner.is_verified:
            return Response(
                {
                    "message":
                    "Venue owner must be verified "
                    "before creating a Razorpay account."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        legal_business_name = request.data.get(
            "legal_business_name"
        )

        business_type = request.data.get(
            "business_type",
            "individual",
        )

        if not legal_business_name:
            legal_business_name = venue_owner.name

        try:
            account = create_linked_account(
                owner=venue_owner,
                legal_business_name=legal_business_name,
                business_type=business_type,
            )

        except Exception as exc:
            return Response(
                {
                    "message":
                    "Unable to create Razorpay linked account.",
                    "error": str(exc),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "message":
                "Razorpay linked account created successfully.",
                "razorpay_account_id":
                account.get("id"),
                "account": account,
            },
            status=status.HTTP_201_CREATED,
        )


class CreateRazorpayStakeholderView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        venue_owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if venue_owner is None:
            return Response(
                {
                    "message":
                    "Only venue owners can create "
                    "a Razorpay stakeholder."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not venue_owner.razorpay_account_id:
            return Response(
                {
                    "message":
                    "Create the Razorpay linked account first."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            stakeholder = create_stakeholder(
                owner=venue_owner,
                percentage_ownership=float(
                    request.data.get(
                        "percentage_ownership",
                        100
                    )
                ),
                is_director=request.data.get(
                    "is_director",
                    True
                ),
                is_executive=request.data.get(
                    "is_executive",
                    False
                ),
            )

        except Exception as exc:
            return Response(
                {
                    "message":
                    "Unable to create Razorpay stakeholder.",
                    "error": str(exc),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "message":
                "Razorpay stakeholder created successfully.",
                "stakeholder_id":
                stakeholder.get(
                    "id",
                    venue_owner.razorpay_stakeholder_id
                ),
                "stakeholder": stakeholder,
            },
            status=status.HTTP_201_CREATED,
        )


class RequestRazorpayRouteProductView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        venue_owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if venue_owner is None:
            return Response(
                {
                    "message":
                    "Only venue owners can configure Razorpay."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            product = request_route_product_configuration(
                owner=venue_owner
            )

        except Exception as exc:
            return Response(
                {
                    "message":
                    "Unable to request Razorpay Route configuration.",
                    "error": str(exc),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "message":
                "Razorpay Route product configuration requested.",
                "product_id":
                product.get(
                    "id",
                    venue_owner.razorpay_product_id
                ),
                "product": product,
            },
            status=status.HTTP_201_CREATED,
        )


class UpdateRazorpayBankDetailsView(APIView):

    permission_classes = [IsAuthenticated]

    def patch(self, request):

        venue_owner = VenueOwner.objects.filter(
            user=request.user
        ).first()

        if venue_owner is None:
            return Response(
                {
                    "message":
                    "Only venue owners can configure bank details."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        account_number = request.data.get(
            "account_number"
        )

        ifsc_code = request.data.get(
            "ifsc_code"
        )

        beneficiary_name = request.data.get(
            "beneficiary_name"
        )

        try:
            result = update_route_product_configuration(
                owner=venue_owner,
                account_number=account_number,
                ifsc_code=ifsc_code,
                beneficiary_name=beneficiary_name,
            )

        except Exception as exc:
            return Response(
                {
                    "message":
                    "Unable to configure Razorpay bank details.",
                    "error": str(exc),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "message":
                "Razorpay bank details submitted successfully.",
                "configuration": result,
            },
            status=status.HTTP_200_OK,
        )