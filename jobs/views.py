import json
import os
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import FileResponse, Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from accounts.models import User

from .forms import ApplicationForm, EmployerProfileForm, JobForm, JobReportForm, JobSearchForm
from .models import Application, Category, EmployerProfile, Job, Payment
from .services import PLANS, activate_payment, create_razorpay_order, verify_payment_signature, verify_webhook_signature


def home(request):
    jobs = Job.objects.filter(status=Job.Status.PUBLISHED).select_related("employer", "category")
    jobs = jobs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))[:8]
    categories = Category.objects.filter(is_active=True).annotate(job_count=Count("jobs", filter=Q(jobs__status=Job.Status.PUBLISHED)))[:8]
    stats = {"jobs": Job.objects.filter(status=Job.Status.PUBLISHED).count(), "employers": EmployerProfile.objects.count()}
    return render(request, "jobs/home.html", {"jobs": jobs, "categories": categories, "stats": stats})


def job_list(request):
    queryset = Job.objects.filter(status=Job.Status.PUBLISHED).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
    queryset = queryset.select_related("employer", "category")
    form = JobSearchForm(request.GET)
    queryset = form.filter(queryset)
    page = Paginator(queryset, 12).get_page(request.GET.get("page"))
    return render(request, "jobs/job_list.html", {"page": page, "search_form": form, "categories": Category.objects.filter(is_active=True)})


def job_detail(request, public_id):
    job = get_object_or_404(Job.objects.select_related("employer", "category"), public_id=public_id)
    if job.status != Job.Status.PUBLISHED and (not request.user.is_authenticated or job.employer.user_id != request.user.id):
        raise Http404
    already_applied = request.user.is_authenticated and Application.objects.filter(job=job, applicant=request.user).exists()
    return render(request, "jobs/job_detail.html", {"job": job, "already_applied": already_applied})


@login_required
def dashboard(request):
    if not request.user.full_name:
        return redirect("accounts:complete_profile")
    if request.user.role == User.Role.EMPLOYER:
        employer, _ = EmployerProfile.objects.get_or_create(user=request.user, defaults={"company_name": request.user.full_name})
        jobs = employer.jobs.annotate(application_count=Count("applications"))
        total_applications = sum(job.application_count for job in jobs)
        return render(request, "jobs/employer_dashboard.html", {"employer": employer, "jobs": jobs, "total_applications": total_applications})
    return render(request, "jobs/seeker_dashboard.html", {"applications": request.user.applications.select_related("job", "job__employer")})


def _employer_for(user):
    if user.role != User.Role.EMPLOYER:
        return None
    employer, _ = EmployerProfile.objects.get_or_create(user=user, defaults={"company_name": user.full_name or "My business"})
    return employer


@login_required
def employer_profile(request):
    employer = _employer_for(request.user)
    if not employer:
        messages.error(request, "ಉದ್ಯೋಗ ಪ್ರಕಟಿಸಲು Employer profile ಆಯ್ಕೆ ಮಾಡಿ.")
        return redirect("accounts:complete_profile")
    form = EmployerProfileForm(request.POST or None, instance=employer)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Company profile updated.")
        return redirect("jobs:dashboard")
    return render(request, "jobs/employer_profile.html", {"form": form, "employer": employer})


@login_required
def job_create(request):
    employer = _employer_for(request.user)
    if not employer:
        messages.error(request, "Employer account is required.")
        return redirect("accounts:complete_profile")
    active_count = employer.jobs.filter(status=Job.Status.PUBLISHED).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())).count()
    active_limit = {EmployerProfile.Plan.FREE: 1, EmployerProfile.Plan.STARTER: 3, EmployerProfile.Plan.BUSINESS: 10}.get(employer.plan, 1)
    if active_count >= active_limit:
        messages.error(request, f"Your current plan allows {active_limit} active job(s). Close a job or upgrade your plan.")
        return redirect("jobs:plans")
    form = JobForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        job = form.save(commit=False)
        job.employer = employer
        job.status = Job.Status.PUBLISHED
        job.is_featured = employer.has_paid_plan
        job.save()
        messages.success(request, "ಉದ್ಯೋಗ ಯಶಸ್ವಿಯಾಗಿ ಪ್ರಕಟಿಸಲಾಗಿದೆ.")
        return redirect(job)
    return render(request, "jobs/job_form.html", {"form": form, "heading": "ಹೊಸ ಉದ್ಯೋಗ ಪ್ರಕಟಿಸಿ"})


@login_required
def job_update(request, public_id):
    employer = _employer_for(request.user)
    job = get_object_or_404(Job, public_id=public_id, employer=employer)
    form = JobForm(request.POST or None, instance=job)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Job updated.")
        return redirect(job)
    return render(request, "jobs/job_form.html", {"form": form, "heading": "ಉದ್ಯೋಗ ತಿದ್ದುಪಡಿ"})


@login_required
@require_POST
def job_close(request, public_id):
    employer = _employer_for(request.user)
    job = get_object_or_404(Job, public_id=public_id, employer=employer)
    job.status = Job.Status.CLOSED
    job.save(update_fields=["status", "updated_at"])
    messages.success(request, "Job closed.")
    return redirect("jobs:dashboard")


@login_required
def apply(request, public_id):
    job = get_object_or_404(Job, public_id=public_id, status=Job.Status.PUBLISHED)
    if request.user.role == User.Role.EMPLOYER:
        messages.error(request, "Employer accounts cannot apply for jobs.")
        return redirect(job)
    if not job.is_open:
        messages.error(request, "ಈ ಉದ್ಯೋಗ ಈಗ ಲಭ್ಯವಿಲ್ಲ.")
        return redirect(job)
    existing = Application.objects.filter(job=job, applicant=request.user).first()
    if existing:
        messages.info(request, "ನೀವು ಈಗಾಗಲೇ ಅರ್ಜಿ ಸಲ್ಲಿಸಿದ್ದೀರಿ.")
        return redirect(job)
    form = ApplicationForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        resume = form.cleaned_data.get("resume")
        if resume:
            request.user.resume = resume
            request.user.save(update_fields=["resume"])
        application = form.save(commit=False)
        application.job = job
        application.applicant = request.user
        application.save()
        messages.success(request, "ಅರ್ಜಿ ಯಶಸ್ವಿಯಾಗಿ ಸಲ್ಲಿಸಲಾಗಿದೆ.")
        if request.POST.get("continue_whatsapp"):
            text = quote(f"Namaskara, I applied for {job.title_en} on Namma Kelasa. My name is {request.user.full_name}.")
            return redirect(f"https://wa.me/91{job.contact_phone}?text={text}")
        return redirect("jobs:dashboard")
    return render(request, "jobs/application_form.html", {"job": job, "form": form})


@login_required
def applicants(request, public_id):
    employer = _employer_for(request.user)
    job = get_object_or_404(Job, public_id=public_id, employer=employer)
    applications = job.applications.select_related("applicant")
    return render(request, "jobs/applicants.html", {"job": job, "applications": applications})


@login_required
def download_resume(request, pk):
    employer = _employer_for(request.user)
    application = get_object_or_404(
        Application.objects.select_related("applicant", "job__employer"),
        pk=pk,
        job__employer=employer,
    )
    resume = application.applicant.resume
    if not resume:
        raise Http404("Candidate has not uploaded a resume.")
    extension = os.path.splitext(resume.name)[1].lower()
    candidate = slugify(application.applicant.full_name) or "candidate"
    return FileResponse(resume.open("rb"), as_attachment=True, filename=f"{candidate}-resume{extension}")


@login_required
@require_POST
def application_status(request, pk):
    employer = _employer_for(request.user)
    application = get_object_or_404(Application, pk=pk, job__employer=employer)
    status = request.POST.get("status")
    if status in Application.Status.values:
        application.status = status
        application.save(update_fields=["status"])
        messages.success(request, "Application status updated.")
    return redirect("jobs:applicants", public_id=application.job.public_id)


@login_required
def report_job(request, public_id):
    job = get_object_or_404(Job, public_id=public_id)
    if job.reports.filter(reporter=request.user).exists():
        messages.info(request, "ನೀವು ಈಗಾಗಲೇ ಈ ಉದ್ಯೋಗವನ್ನು report ಮಾಡಿದ್ದೀರಿ.")
        return redirect(job)
    form = JobReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        report = form.save(commit=False)
        report.job = job
        report.reporter = request.user
        report.save()
        messages.success(request, "ವರದಿ ಸ್ವೀಕರಿಸಲಾಗಿದೆ. ನಾವು ಪರಿಶೀಲಿಸುತ್ತೇವೆ.")
        return redirect(job)
    return render(request, "jobs/report_form.html", {"form": form, "job": job})


def plans(request):
    return render(request, "jobs/plans.html", {"plans": PLANS})


@login_required
@require_POST
def purchase_plan(request, plan):
    employer = _employer_for(request.user)
    if not employer:
        return redirect("accounts:complete_profile")
    plan_data = PLANS.get(plan)
    if not plan_data:
        raise Http404
    try:
        order = create_razorpay_order(plan_data["amount_paise"], f"nk-{employer.pk}-{int(timezone.now().timestamp())}")
    except RuntimeError as exc:
        messages.error(request, str(exc))
        return redirect("jobs:plans")
    payment = Payment.objects.create(
        employer=employer, plan=plan, amount_paise=plan_data["amount_paise"], gateway_order_id=order["id"]
    )
    return render(request, "jobs/checkout.html", {"payment": payment, "key_id": settings.RAZORPAY_KEY_ID, "plan_data": plan_data})


@login_required
@require_POST
def payment_success(request):
    order_id = request.POST.get("razorpay_order_id", "")
    payment_id = request.POST.get("razorpay_payment_id", "")
    signature = request.POST.get("razorpay_signature", "")
    payment = get_object_or_404(Payment, gateway_order_id=order_id, employer__user=request.user)
    if not verify_payment_signature(order_id, payment_id, signature):
        return HttpResponseBadRequest("Invalid payment signature")
    activate_payment(payment, payment_id)
    messages.success(request, "Payment successful. Your plan is active.")
    return redirect("jobs:dashboard")


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        return HttpResponseBadRequest("Webhook not configured")
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not verify_webhook_signature(request.body, signature):
        return HttpResponseBadRequest("Invalid signature")
    event = json.loads(request.body)
    if event.get("event") == "payment.captured":
        entity = event.get("payload", {}).get("payment", {}).get("entity", {})
        payment = Payment.objects.filter(gateway_order_id=entity.get("order_id")).first()
        if payment:
            activate_payment(payment, entity.get("id", ""))
    return HttpResponse("ok")


def set_language(request, lang):
    if lang in {"kn", "en"}:
        request.session["lang"] = lang
        if request.user.is_authenticated:
            request.user.preferred_language = lang
            request.user.save(update_fields=["preferred_language"])
    next_url = request.GET.get("next", reverse("jobs:home"))
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = reverse("jobs:home")
    return redirect(next_url)


def static_page(request, page):
    if page not in {"about", "safety", "privacy", "terms", "contact"}:
        raise Http404
    return render(request, f"jobs/static/{page}.html")
