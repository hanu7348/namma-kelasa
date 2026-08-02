import logging
import secrets
from datetime import timedelta

import resend
from resend.exceptions import ResendError

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from .models import OTPChallenge

logger = logging.getLogger(__name__)


def _resend_error_message(exc):
    error_name = str(getattr(exc, "error_type", "unknown_error"))
    provider_message = str(getattr(exc, "message", str(exc)))
    normalized = provider_message.lower()
    status = getattr(exc, "code", "unknown")
    logger.warning("Resend rejected OTP email: status=%s type=%s", status, error_name)
    if "only send testing emails to your own email" in normalized or "verify a domain" in normalized:
        return "Resend testing can only deliver to the email registered on the same Resend account as this API key. Verify a domain to send to other addresses."
    if "api key is invalid" in normalized or error_name == "invalid_api_key":
        return "Resend rejected the API key. Create a new sending key, update .env, and restart Django."
    if "domain" in normalized and "not verified" in normalized:
        return "The Resend sender domain is not verified. Verify it in Resend or use onboarding@resend.dev for the account-owner email."
    if status == 429 or error_name in {"rate_limit_exceeded", "daily_quota_exceeded", "monthly_quota_exceeded"}:
        return "Resend has temporarily rate-limited email delivery. Please wait and try again."
    if error_name == "HttpClientError":
        return "The email service could not be reached. Please try again shortly."
    return f"Resend rejected the email (HTTP {status}, {error_name}). Check the Resend dashboard logs for details."


def _email_html(code):
    return f"""<!doctype html><html><body style="margin:0;background:#f3f5fb;font-family:Arial,sans-serif;color:#17213a"><div style="max-width:560px;margin:40px auto;background:#fff;border-radius:20px;padding:36px;border:1px solid #e3e8f2"><div style="display:inline-block;background:#5b5cf0;color:#fff;border-radius:12px;padding:10px 14px;font-weight:800">ನಮ್ಮ ಕೆಲಸ</div><h1 style="font-size:26px;margin:28px 0 8px">Your sign-in code</h1><p style="color:#657089">ಈ code ಅನ್ನು Namma Kelasa login pageನಲ್ಲಿ ನಮೂದಿಸಿ.</p><div style="font-size:36px;letter-spacing:10px;font-weight:800;background:#f1f2ff;color:#4f46e5;border-radius:14px;padding:20px;text-align:center;margin:24px 0">{code}</div><p style="font-size:13px;color:#7d8799">This code expires in 5 minutes. If you did not request it, you can ignore this email.</p></div></body></html>"""


def _send_with_resend(email, code, challenge_id):
    if not settings.RESEND_API_KEY:
        raise RuntimeError("Email service is not configured.")
    resend.api_key = settings.RESEND_API_KEY
    params: resend.Emails.SendParams = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": [email],
        "subject": f"{code} is your Namma Kelasa sign-in code",
        "html": _email_html(code),
    }
    options: resend.Emails.SendOptions = {
        "idempotency_key": f"namma-kelasa-otp-{challenge_id}",
    }
    try:
        return resend.Emails.send(params, options)
    except ResendError as exc:
        raise RuntimeError(_resend_error_message(exc)) from exc
    except (ConnectionError, TimeoutError) as exc:
        logger.warning("Resend network failure for challenge %s: %s", challenge_id, exc)
        raise RuntimeError("The email service could not be reached. Please try again shortly.") from exc


def create_and_send_otp(email):
    email = email.strip().lower()
    if OTPChallenge.recent_count(email) >= 3:
        raise ValueError("Too many OTP requests. Please wait 10 minutes.")
    OTPChallenge.objects.filter(email=email, consumed_at__isnull=True).update(consumed_at=timezone.now())
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = OTPChallenge.objects.create(
        email=email,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(minutes=settings.OTP_TTL_MINUTES),
    )
    if settings.OTP_BACKEND == "console":
        logger.warning("Namma Kelasa OTP for %s is %s", email, code)
        print(f"\n[NAMMA KELASA DEV OTP] {email}: {code}\n")
    elif settings.OTP_BACKEND == "resend":
        try:
            _send_with_resend(email, code, challenge.pk)
        except RuntimeError:
            challenge.consumed_at = timezone.now()
            challenge.save(update_fields=["consumed_at"])
            raise
    else:
        raise RuntimeError("Unsupported OTP email backend.")
    return challenge
