import base64
import hashlib
import hmac
import json
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from .models import EmployerProfile, Payment


PLANS = {
    "starter": {"name": "Starter", "amount_paise": 199900, "featured_jobs": 3},
    "business": {"name": "Business", "amount_paise": 299900, "featured_jobs": 10},
}


def create_razorpay_order(amount_paise, receipt):
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise RuntimeError("Razorpay keys are not configured.")
    payload = json.dumps({"amount": amount_paise, "currency": "INR", "receipt": receipt}).encode()
    credentials = base64.b64encode(f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}".encode()).decode()
    request = Request(
        "https://api.razorpay.com/v1/orders",
        data=payload,
        headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode())
    except (HTTPError, URLError) as exc:
        raise RuntimeError("Payment gateway could not create an order.") from exc


def verify_payment_signature(order_id, payment_id, signature):
    message = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(body, signature):
    expected = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def activate_payment(payment, payment_id):
    if payment.status == Payment.Status.PAID:
        return payment
    payment.status = Payment.Status.PAID
    payment.gateway_payment_id = payment_id
    payment.paid_at = timezone.now()
    payment.save(update_fields=["status", "gateway_payment_id", "paid_at"])
    employer = payment.employer
    employer.plan = payment.plan
    start = employer.plan_expires_at if employer.plan_expires_at and employer.plan_expires_at > timezone.now() else timezone.now()
    employer.plan_expires_at = start + timedelta(days=30)
    employer.save(update_fields=["plan", "plan_expires_at"])
    return payment
