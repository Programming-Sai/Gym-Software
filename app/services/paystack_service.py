import requests
import hashlib
import hmac
from decimal import Decimal
from fastapi import HTTPException
from app.core.config import settings


PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackService:
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.public_key = settings.PAYSTACK_PUBLIC_KEY

        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    # -------------------------------------------------
    # INITIALIZE TRANSACTION
    # -------------------------------------------------
    def initialize_transaction(
        self,
        email: str,
        amount: Decimal,
        reference: str,
        callback_url: str,
        metadata: dict | None = None,
        channels: list[str] | None = None,
    ):
        payload = {
            "email": email,
            "amount": int(amount * 100),  # Convert GHS to pesewas
            "currency": "GHS",
            "reference": reference,
        }

        if callback_url:
            payload["callback_url"] = callback_url

        if metadata:
            payload["metadata"] = metadata

        if channels:
            payload["channels"] = channels

        response = requests.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            headers=self.headers,
            json=payload,
            timeout=30,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize Paystack transaction",
            )

        data = response.json()

        if not data.get("status"):
            raise HTTPException(
                status_code=400,
                detail=data.get("message", "Paystack initialization failed"),
            )

        return data["data"]

    # -------------------------------------------------
    # VERIFY TRANSACTION
    # -------------------------------------------------
    def verify_transaction(self, reference: str):
        response = requests.get(
            f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
            headers=self.headers,
            timeout=30,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Failed to verify Paystack transaction",
            )

        data = response.json()

        if not data.get("status"):
            raise HTTPException(
                status_code=400,
                detail=data.get("message", "Transaction verification failed"),
            )

        return data["data"]

    # -------------------------------------------------
    # VERIFY WEBHOOK SIGNATURE
    # -------------------------------------------------
    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        computed_hash = hmac.new(
            key=self.secret_key.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha512,
        ).hexdigest()

        return hmac.compare_digest(computed_hash, signature)

    # -------------------------------------------------
    # CREATE TRANSFER (FOR GYM PAYOUTS)
    # -------------------------------------------------
    def create_transfer(self, amount: Decimal, recipient_code: str, reference: str):
        payload = {
            "source": "balance",
            "amount": int(amount * 100),  # pesewas
            "recipient": recipient_code,
            "reference": reference,
            "currency": "GHS",
        }

        response = requests.post(
            f"{PAYSTACK_BASE_URL}/transfer",
            headers=self.headers,
            json=payload,
            timeout=30,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Failed to create Paystack transfer",
            )

        data = response.json()

        if not data.get("status"):
            raise HTTPException(
                status_code=400,
                detail=data.get("message", "Transfer failed"),
            )

        return data["data"]
