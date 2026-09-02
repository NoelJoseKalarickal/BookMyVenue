import requests

from django.conf import settings


RAZORPAY_API = "https://api.razorpay.com"


def razorpay_auth():
    return (
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET,
    )


def check_credentials():
    if not settings.RAZORPAY_KEY_ID:
        raise ValueError("RAZORPAY_KEY_ID is not configured.")

    if not settings.RAZORPAY_KEY_SECRET:
        raise ValueError("RAZORPAY_KEY_SECRET is not configured.")


def create_linked_account(
    owner,
    legal_business_name,
    business_type="individual",
):
    check_credentials()

    if not owner.user.email:
        raise ValueError(
            "Venue owner must have an email address."
        )

    if not owner.phone_number:
        raise ValueError(
            "Venue owner must have a phone number."
        )

    if not legal_business_name:
        legal_business_name = owner.name

    payload = {
        "email": owner.user.email,
        "phone": owner.phone_number,
        "type": "route",
        "reference_id": str(owner.id),
        "legal_business_name": legal_business_name,
        "customer_facing_business_name": legal_business_name,
        "business_type": business_type,
    }

    response = requests.post(
        f"{RAZORPAY_API}/v2/accounts",
        json=payload,
        auth=razorpay_auth(),
        timeout=30,
    )

    if not response.ok:
        raise ValueError(
            f"Razorpay error: {response.text}"
        )

    data = response.json()

    account_id = data.get("id")

    if not account_id:
        raise ValueError(
            "Razorpay did not return a linked account ID."
        )

    owner.razorpay_account_id = account_id
    owner.save(
        update_fields=["razorpay_account_id"]
    )

    return data


def create_stakeholder(
    owner,
    percentage_ownership=100,
    is_director=True,
    is_executive=False,
):
    check_credentials()

    if not owner.razorpay_account_id:
        raise ValueError(
            "Razorpay linked account must be created first."
        )

    if owner.razorpay_stakeholder_id:
        return {
            "id": owner.razorpay_stakeholder_id,
            "message": "Stakeholder already exists.",
        }

    if not owner.user.email:
        raise ValueError(
            "Venue owner must have an email address."
        )

    if not owner.phone_number:
        raise ValueError(
            "Venue owner must have a phone number."
        )

    payload = {
        "name": owner.name,
        "email": owner.user.email,
        "percentage_ownership": percentage_ownership,
        "relationship": {
            "director": is_director,
            "executive": is_executive,
        },
        "phone": {
            "primary": owner.phone_number,
        },
        "addresses": {
            "registered": {
                "street": owner.address_line_1,
                "city": "",
                "state": "",
                "postal_code": "",
                "country": "IN",
            }
        },
        "notes": {
            "source": "BookMyVenue",
            "owner_id": str(owner.id),
        },
    }

    response = requests.post(
        f"{RAZORPAY_API}/v2/accounts/"
        f"{owner.razorpay_account_id}/stakeholders",
        json=payload,
        auth=razorpay_auth(),
        timeout=30,
    )

    if not response.ok:
        raise ValueError(
            f"Razorpay stakeholder error: {response.text}"
        )

    data = response.json()

    stakeholder_id = data.get("id")

    if not stakeholder_id:
        raise ValueError(
            "Razorpay did not return a stakeholder ID."
        )

    owner.razorpay_stakeholder_id = stakeholder_id

    owner.save(
        update_fields=[
            "razorpay_stakeholder_id",
        ]
    )

    return data


def request_route_product_configuration(owner):
    check_credentials()

    if not owner.razorpay_account_id:
        raise ValueError(
            "Razorpay linked account must be created first."
        )

    if not owner.razorpay_stakeholder_id:
        raise ValueError(
            "Razorpay stakeholder must be created first."
        )

    if owner.razorpay_product_id:
        return {
            "id": owner.razorpay_product_id,
            "message": "Route product already requested.",
        }

    payload = {
        "product_name": "route",
        "tnc_accepted": True,
    }

    response = requests.post(
        f"{RAZORPAY_API}/v2/accounts/"
        f"{owner.razorpay_account_id}/products",
        json=payload,
        auth=razorpay_auth(),
        timeout=30,
    )

    if not response.ok:
        raise ValueError(
            f"Razorpay product configuration error: "
            f"{response.text}"
        )

    data = response.json()

    product_id = data.get("id")

    if not product_id:
        raise ValueError(
            "Razorpay did not return a product ID."
        )

    owner.razorpay_product_id = product_id

    owner.save(
        update_fields=[
            "razorpay_product_id",
        ]
    )

    return data


def update_route_product_configuration(
    owner,
    account_number,
    ifsc_code,
    beneficiary_name,
):
    check_credentials()

    if not owner.razorpay_account_id:
        raise ValueError(
            "Razorpay linked account must be created first."
        )

    if not owner.razorpay_product_id:
        raise ValueError(
            "Razorpay Route product must be requested first."
        )

    if not account_number:
        raise ValueError(
            "Bank account number is required."
        )

    if not ifsc_code:
        raise ValueError(
            "IFSC code is required."
        )

    if not beneficiary_name:
        raise ValueError(
            "Beneficiary name is required."
        )

    payload = {
        "settlements": {
            "account_number": account_number,
            "ifsc_code": ifsc_code,
            "beneficiary_name": beneficiary_name,
        }
    }

    response = requests.patch(
        f"{RAZORPAY_API}/v2/accounts/"
        f"{owner.razorpay_account_id}/products/"
        f"{owner.razorpay_product_id}",
        json=payload,
        auth=razorpay_auth(),
        timeout=30,
    )

    if not response.ok:
        raise ValueError(
            f"Razorpay bank configuration error: "
            f"{response.text}"
        )

    return response.json()


def transfer_payment_to_owner(
    razorpay_payment_id,
    razorpay_account_id,
    amount,
):
    check_credentials()

    if not razorpay_payment_id:
        raise ValueError(
            "Razorpay payment ID is required."
        )

    if not razorpay_account_id:
        raise ValueError(
            "Razorpay linked account ID is required."
        )

    amount_paise = int(amount * 100)

    if amount_paise < 100:
        raise ValueError(
            "Transfer amount must be at least ₹1."
        )

    payload = {
        "transfers": [
            {
                "account": razorpay_account_id,
                "amount": amount_paise,
                "currency": "INR",
                "notes": {
                    "source": "BookMyVenue",
                },
            }
        ]
    }

    response = requests.post(
        f"{RAZORPAY_API}/v1/payments/"
        f"{razorpay_payment_id}/transfers",
        json=payload,
        auth=razorpay_auth(),
        timeout=30,
    )

    if not response.ok:
        raise ValueError(
            f"Razorpay transfer error: {response.text}"
        )

    return response.json()