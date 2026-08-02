import hashlib
import hmac
from datetime import timedelta
from unittest.mock import patch

from resend.exceptions import ResendError

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import OTPChallenge, User
from accounts.services import create_and_send_otp
from jobs.models import Application, Category, EmployerProfile, Job, JobReport
from jobs.services import verify_payment_signature


class JobSiteTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name_kn="ಅಂಗಡಿ", name_en="Retail", slug="retail", icon="🏪")
        self.employer_user = User.objects.create_user(email="employer@example.com", full_name="Employer", role=User.Role.EMPLOYER)
        self.employer = EmployerProfile.objects.get(user=self.employer_user)
        self.employer.company_name = "Test Company"
        self.employer.is_verified = True
        self.employer.save()
        self.seeker = User.objects.create_user(email="seeker@example.com", full_name="Seeker", role=User.Role.JOB_SEEKER)
        self.job = Job.objects.create(
            employer=self.employer, category=self.category, title_kn="ಅಂಗಡಿ ಸಹಾಯಕ", title_en="Shop Assistant",
            description_kn="ವಿವರ", description_en="Description", job_type=Job.JobType.FULL_TIME,
            salary_min=15000, salary_max=18000, salary_period=Job.SalaryPeriod.MONTH,
            city="Mysuru", area="Vijayanagar", contact_phone="9876543210", expires_at=timezone.now() + timedelta(days=7),
        )

    def test_public_pages_and_search(self):
        self.assertEqual(self.client.get(reverse("jobs:home")).status_code, 200)
        response = self.client.get(reverse("jobs:list"), {"city": "Mysuru"})
        self.assertContains(response, "ಅಂಗಡಿ ಸಹಾಯಕ")
        response = self.client.get(reverse("jobs:list"), {"city": "Bengaluru"})
        self.assertNotContains(response, "ಅಂಗಡಿ ಸಹಾಯಕ")

    def test_seeker_can_apply_only_once(self):
        self.client.force_login(self.seeker)
        url = reverse("jobs:apply", kwargs={"public_id": self.job.public_id})
        self.assertEqual(self.client.post(url, {"note": "Available now"}).status_code, 302)
        self.assertEqual(self.client.post(url, {"note": "Again"}).status_code, 302)
        self.assertEqual(Application.objects.filter(job=self.job, applicant=self.seeker).count(), 1)

    def test_seeker_can_apply_with_private_resume_and_owner_can_download(self):
        resume = SimpleUploadedFile("arya-resume.pdf", b"%PDF-1.4\n% test resume\n%%EOF", content_type="application/pdf")
        self.client.force_login(self.seeker)
        response = self.client.post(
            reverse("jobs:apply", kwargs={"public_id": self.job.public_id}),
            {"note": "Resume attached", "resume": resume},
        )
        self.assertEqual(response.status_code, 302)
        self.seeker.refresh_from_db()
        self.assertTrue(self.seeker.resume)
        self.assertTrue(self.seeker.resume.path.startswith(str(settings.PRIVATE_MEDIA_ROOT)))
        self.assertEqual(self.client.get(reverse("accounts:complete_profile")).status_code, 200)

        application = Application.objects.get(job=self.job, applicant=self.seeker)
        self.client.force_login(self.employer_user)
        response = self.client.get(reverse("jobs:download_resume", kwargs={"pk": application.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["Content-Disposition"])
        response.close()

        other = User.objects.create_user(email="resume-other@example.com", full_name="Other", role=User.Role.EMPLOYER)
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("jobs:download_resume", kwargs={"pk": application.pk})).status_code, 404)
        self.seeker.resume.delete(save=False)

    def test_fake_pdf_resume_is_rejected(self):
        resume = SimpleUploadedFile("resume.pdf", b"not really a pdf", content_type="application/pdf")
        self.client.force_login(self.seeker)
        response = self.client.post(
            reverse("jobs:apply", kwargs={"public_id": self.job.public_id}),
            {"note": "Invalid file", "resume": resume},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not a valid PDF")
        self.assertFalse(Application.objects.filter(job=self.job, applicant=self.seeker).exists())

    def test_employer_cannot_apply(self):
        self.client.force_login(self.employer_user)
        response = self.client.post(reverse("jobs:apply", kwargs={"public_id": self.job.public_id}), {"note": "No"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Application.objects.filter(job=self.job, applicant=self.employer_user).exists())

    def test_job_report(self):
        self.client.force_login(self.seeker)
        response = self.client.post(reverse("jobs:report", kwargs={"public_id": self.job.public_id}), {"reason": "fake", "details": "Suspicious"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(JobReport.objects.filter(job=self.job, reporter=self.seeker).exists())

    def test_employer_can_edit_own_job_but_not_other(self):
        self.client.force_login(self.employer_user)
        self.assertEqual(self.client.get(reverse("jobs:update", kwargs={"public_id": self.job.public_id})).status_code, 200)
        other = User.objects.create_user(email="other@example.com", full_name="Other", role=User.Role.EMPLOYER)
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("jobs:update", kwargs={"public_id": self.job.public_id})).status_code, 404)

    def test_language_switch(self):
        response = self.client.get(reverse("jobs:set_language", kwargs={"lang": "en"}), {"next": "/jobs/"})
        self.assertRedirects(response, "/jobs/")
        self.assertEqual(self.client.session["lang"], "en")

    def test_key_templates_render_for_both_roles(self):
        public_urls = [
            reverse("jobs:detail", kwargs={"public_id": self.job.public_id}),
            reverse("jobs:plans"), reverse("accounts:request_otp"),
            reverse("jobs:static_page", kwargs={"page": "safety"}),
            reverse("jobs:static_page", kwargs={"page": "privacy"}),
        ]
        for url in public_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

        self.client.force_login(self.seeker)
        self.assertEqual(self.client.get(reverse("jobs:dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("jobs:apply", kwargs={"public_id": self.job.public_id})).status_code, 200)
        Application.objects.create(job=self.job, applicant=self.seeker)

        self.client.force_login(self.employer_user)
        self.assertEqual(self.client.get(reverse("jobs:dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("jobs:employer_profile")).status_code, 200)
        self.assertEqual(self.client.get(reverse("jobs:applicants", kwargs={"public_id": self.job.public_id})).status_code, 200)

    @override_settings(RAZORPAY_KEY_SECRET="test-secret")
    def test_payment_signature(self):
        order_id, payment_id = "order_1", "pay_1"
        signature = hmac.new(b"test-secret", f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
        self.assertTrue(verify_payment_signature(order_id, payment_id, signature))
        self.assertFalse(verify_payment_signature(order_id, payment_id, "wrong"))


class OTPTests(TestCase):
    def test_valid_challenge_property(self):
        challenge = OTPChallenge.objects.create(
            email="person@example.com", code_hash=make_password("123456"), expires_at=timezone.now() + timedelta(minutes=5)
        )
        self.assertTrue(challenge.is_valid)
        challenge.attempts = 5
        self.assertFalse(challenge.is_valid)

    def test_otp_login_creates_user_and_opens_onboarding(self):
        def fake_send(email):
            return OTPChallenge.objects.create(
                email=email, code_hash=make_password("123456"), expires_at=timezone.now() + timedelta(minutes=5)
            )

        with patch("accounts.views.create_and_send_otp", side_effect=fake_send):
            response = self.client.post(reverse("accounts:request_otp"), {"email": "new@example.com"})
        self.assertRedirects(response, reverse("accounts:verify_otp"))
        response = self.client.post(reverse("accounts:verify_otp"), {"code": "123456"})
        self.assertRedirects(response, reverse("accounts:complete_profile"))
        self.assertTrue(User.objects.filter(email="new@example.com").exists())
        self.assertGreaterEqual(self.client.session.get_expiry_age(), 29 * 24 * 60 * 60)

    def test_authenticated_user_skips_login_page(self):
        user = User.objects.create_user(email="returning@example.com", full_name="Returning user")
        self.client.force_login(user)
        self.assertRedirects(self.client.get(reverse("accounts:request_otp")), reverse("jobs:dashboard"))

    @override_settings(DEBUG=True, SITE_URL="http://127.0.0.1:8000")
    def test_localhost_redirects_to_canonical_cookie_host(self):
        response = self.client.get(reverse("accounts:request_otp"), HTTP_HOST="localhost:8000")
        self.assertRedirects(
            response,
            "http://127.0.0.1:8000/account/login/",
            fetch_redirect_response=False,
        )

    @override_settings(OTP_BACKEND="resend", RESEND_API_KEY="test-key", RESEND_FROM_EMAIL="Login <login@example.com>")
    @patch("accounts.services.resend.Emails.send")
    def test_resend_delivery_is_server_side(self, mock_send):
        mock_send.return_value = {"id": "email_test"}
        challenge = create_and_send_otp("person@example.com")
        self.assertEqual(challenge.email, "person@example.com")
        params, options = mock_send.call_args.args
        self.assertEqual(params["to"], ["person@example.com"])
        self.assertEqual(params["from"], "Login <login@example.com>")
        self.assertNotIn("test-key", str(params))
        self.assertEqual(options["idempotency_key"], f"namma-kelasa-otp-{challenge.pk}")

    @override_settings(OTP_BACKEND="resend", RESEND_API_KEY="test-key", RESEND_FROM_EMAIL="Login <onboarding@resend.dev>")
    @patch("accounts.services.resend.Emails.send")
    def test_resend_403_explains_testing_restriction(self, mock_send):
        mock_send.side_effect = ResendError(
            code=403,
            error_type="validation_error",
            message="You can only send testing emails to your own email address. To send emails to other recipients, please verify a domain.",
            suggested_action="Verify a domain.",
        )
        with self.assertRaisesRegex(RuntimeError, "same Resend account"):
            create_and_send_otp("person@example.com")
