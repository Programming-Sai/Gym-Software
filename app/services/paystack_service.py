import requests
import hashlib
import hmac
from decimal import Decimal
from fastapi import HTTPException
from app.core.config import settings
from typing import Any, Optional


PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackService:
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.public_key = settings.PAYSTACK_PUBLIC_KEY

        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def _raise_for_paystack_error(self, response: requests.Response, fallback_message: str) -> None:
        try:
            payload = response.json()
        except Exception:
            payload = None

        message = None
        if isinstance(payload, dict):
            message = payload.get("message")

        raise HTTPException(
            status_code=500,
            detail=message or fallback_message,
        )

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
    # TRANSFER RECIPIENTS
    # -------------------------------------------------
    def create_transfer_recipient(
        self,
        *,
        recipient_type: str,
        name: str,
        account_number: Optional[str] = None,
        bank_code: Optional[str] = None,
        currency: str = "GHS",
        description: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Create a Paystack transfer recipient.

        Paystack expects:
        - type: one of "nuban", "ghipss", "mobile_money", "basa", "authorization"
        - name
        - account_number + bank_code for most types (mobile_money uses telco as bank_code)
        """
        payload: dict[str, Any] = {
            "type": recipient_type,
            "name": name,
            "currency": currency,
        }

        if account_number is not None:
            payload["account_number"] = account_number
        if bank_code is not None:
            payload["bank_code"] = bank_code
        if description is not None:
            payload["description"] = description
        if metadata is not None:
            payload["metadata"] = metadata

        response = requests.post(
            f"{PAYSTACK_BASE_URL}/transferrecipient",
            headers=self.headers,
            json=payload,
            timeout=30,
        )

        if response.status_code not in (200, 201):
            self._raise_for_paystack_error(response, "Failed to create Paystack transfer recipient")

        data = response.json()
        
        if not data.get("status"):
            raise HTTPException(status_code=400, detail=data.get("message", "Transfer recipient creation failed"))

        return data["data"]

    def delete_transfer_recipient(self, id_or_code: str) -> dict[str, Any]:
        """
        Delete (deactivate) a Paystack transfer recipient.
        Paystack semantics: sets the recipient inactive.
        """
        response = requests.delete(
            f"{PAYSTACK_BASE_URL}/transferrecipient/{id_or_code}",
            headers=self.headers,
            timeout=30,
        )

        if response.status_code != 200:
            self._raise_for_paystack_error(response, "Failed to delete Paystack transfer recipient")

        data = response.json()
        if not data.get("status"):
            raise HTTPException(status_code=400, detail=data.get("message", "Transfer recipient deletion failed"))

        return data.get("data") or {"message": data.get("message")}

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
    # VERIFY TRANSFER (PAYOUTS)
    # -------------------------------------------------
    def verify_transfer(self, reference: str) -> dict[str, Any]:
        """
        Verify a Paystack transfer by reference.

        Note: This is different from transaction verification (payments).
        """
        response = requests.get(
            f"{PAYSTACK_BASE_URL}/transfer/verify/{reference}",
            headers=self.headers,
            timeout=30,
        )

        if response.status_code != 200:
            self._raise_for_paystack_error(response, "Failed to verify Paystack transfer")

        data = response.json()

        if not data.get("status"):
            raise HTTPException(
                status_code=400,
                detail=data.get("message", "Transfer verification failed"),
            )

        return data["data"]

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

        if response.status_code not in (200, 201):
            self._raise_for_paystack_error(response, "Failed to create Paystack transfer")

        data = response.json()

        if not data.get("status"):
            raise HTTPException(
                status_code=400,
                detail=data.get("message", "Transfer failed"),
            )

        return data["data"]
