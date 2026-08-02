from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import CompleteProfileForm, EmailForm, VerifyOTPForm
from .models import OTPChallenge, User
from .services import create_and_send_otp


def request_otp(request):
    if request.user.is_authenticated:
        return redirect("jobs:dashboard")
    form = EmailForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        try:
            challenge = create_and_send_otp(email)
        except (ValueError, RuntimeError) as exc:
            form.add_error("email", str(exc))
        else:
            request.session["otp_challenge_id"] = challenge.pk
            request.session["otp_email"] = email
            return redirect("accounts:verify_otp")
    return render(request, "accounts/request_otp.html", {"form": form})


def verify_otp(request):
    challenge_id = request.session.get("otp_challenge_id")
    email = request.session.get("otp_email")
    if not challenge_id or not email:
        return redirect("accounts:request_otp")
    challenge = OTPChallenge.objects.filter(pk=challenge_id, email=email).first()
    if not challenge or not challenge.is_valid:
        messages.error(request, "OTP ಅವಧಿ ಮುಗಿದಿದೆ. ಹೊಸ OTP ಪಡೆಯಿರಿ.")
        return redirect("accounts:request_otp")
    form = VerifyOTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        challenge.attempts += 1
        challenge.save(update_fields=["attempts"])
        if check_password(form.cleaned_data["code"], challenge.code_hash):
            challenge.consumed_at = timezone.now()
            challenge.save(update_fields=["consumed_at"])
            user, created = User.objects.get_or_create(email=email, defaults={"full_name": ""})
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            request.session.pop("otp_challenge_id", None)
            request.session.pop("otp_email", None)
            return redirect("accounts:complete_profile" if created or not user.full_name else "jobs:dashboard")
        form.add_error("code", "ತಪ್ಪಾದ OTP. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.")
    return render(request, "accounts/verify_otp.html", {"form": form, "email": email})


@login_required
def complete_profile(request):
    form = CompleteProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "ನಿಮ್ಮ ಪ್ರೊಫೈಲ್ ಸಿದ್ಧವಾಗಿದೆ.")
        return redirect("jobs:dashboard")
    return render(request, "accounts/complete_profile.html", {"form": form})


def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("jobs:home")
