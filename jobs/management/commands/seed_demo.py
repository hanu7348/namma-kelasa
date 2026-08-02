from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import User
from jobs.models import Application, Category, EmployerProfile, Job


CATEGORIES = [
    ("retail", "ಅಂಗಡಿ ಮತ್ತು ರೀಟೇಲ್", "Retail & shop", "🏪"),
    ("delivery", "ಡೆಲಿವರಿ", "Delivery", "🛵"),
    ("hospitality", "ಹೋಟೆಲ್ ಮತ್ತು ಅಡುಗೆ", "Hotel & kitchen", "🍛"),
    ("driver", "ಡ್ರೈವರ್", "Driver", "🚕"),
    ("office", "ಆಫೀಸ್ ಸಹಾಯಕ", "Office support", "💻"),
    ("security", "ಸೆಕ್ಯೂರಿಟಿ", "Security", "🛡️"),
    ("technician", "ಟೆಕ್ನಿಷಿಯನ್", "Technician", "🔧"),
    ("education", "ಶಿಕ್ಷಣ", "Education", "📚"),
]

JOBS = [
    ("retail", "ಅಂಗಡಿ ಸಹಾಯಕ", "Shop Assistant", "Mysuru", "Kuvempunagar", 15000, 18000, "full_time"),
    ("delivery", "ಡೆಲಿವರಿ ಪಾರ್ಟ್ನರ್", "Delivery Partner", "Bengaluru", "Jayanagar", 22000, 32000, "full_time"),
    ("hospitality", "ಹೋಟೆಲ್ ಸರ್ವರ್", "Restaurant Server", "Mangaluru", "Hampankatta", 14000, 18000, "full_time"),
    ("driver", "ಕ್ಯಾಬ್ ಡ್ರೈವರ್", "Cab Driver", "Bengaluru", "Yelahanka", 20000, 30000, "full_time"),
    ("office", "ಡೇಟಾ ಎಂಟ್ರಿ ಸಹಾಯಕ", "Data Entry Assistant", "Hubballi", "Vidya Nagar", 16000, 21000, "full_time"),
    ("security", "ಸೆಕ್ಯೂರಿಟಿ ಗಾರ್ಡ್", "Security Guard", "Belagavi", "Tilakwadi", 17000, 21000, "full_time"),
    ("technician", "ಎಲೆಕ್ಟ್ರಿಷಿಯನ್", "Electrician", "Mysuru", "Vijayanagar", 800, 1200, "daily"),
    ("education", "ಕನ್ನಡ ಟ್ಯೂಟರ್", "Kannada Tutor", "Bengaluru", "Rajajinagar", 350, 600, "part_time"),
]


class Command(BaseCommand):
    help = "Create idempotent demo categories, users and jobs"

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo data cannot be seeded when DJANGO_DEBUG=False.")
        categories = {}
        for slug, name_kn, name_en, icon in CATEGORIES:
            categories[slug], _ = Category.objects.update_or_create(slug=slug, defaults={"name_kn": name_kn, "name_en": name_en, "icon": icon})

        employer_user, _ = User.objects.get_or_create(
            email="employer@example.com",
            defaults={"full_name": "ರವಿ ಕುಮಾರ್", "role": User.Role.EMPLOYER},
        )
        if employer_user.role != User.Role.EMPLOYER:
            employer_user.role = User.Role.EMPLOYER
            employer_user.save(update_fields=["role"])
        employer, _ = EmployerProfile.objects.update_or_create(
            user=employer_user,
            defaults={"company_name": "ಕರ್ನಾಟಕ ಲೋಕಲ್ ಸರ್ವಿಸಸ್", "contact_person": "Ravi Kumar", "city": "Mysuru", "is_verified": True},
        )

        for index, (category, title_kn, title_en, city, area, salary_min, salary_max, job_type) in enumerate(JOBS):
            period = Job.SalaryPeriod.DAY if job_type == "daily" else Job.SalaryPeriod.HOUR if job_type == "part_time" else Job.SalaryPeriod.MONTH
            Job.objects.update_or_create(
                employer=employer,
                title_en=title_en,
                defaults={
                    "category": categories[category], "title_kn": title_kn,
                    "description_kn": f"{title_kn} ಹುದ್ದೆಗೆ ವಿಶ್ವಾಸಾರ್ಹ ಅಭ್ಯರ್ಥಿಗಳು ಬೇಕಾಗಿದ್ದಾರೆ. ಅನುಭವ ಇದ್ದರೆ ಉತ್ತಮ; ತರಬೇತಿ ನೀಡಲಾಗುತ್ತದೆ.",
                    "description_en": f"We are hiring a reliable {title_en}. Prior experience is helpful; role training will be provided.",
                    "job_type": job_type, "salary_min": salary_min, "salary_max": salary_max,
                    "salary_period": period, "vacancies": 2, "city": city, "area": area,
                    "address": f"{area}, {city}, Karnataka", "contact_phone": "9876543210",
                    "requirements": "18+ years. Valid identity document. Kannada communication preferred.",
                    "status": Job.Status.PUBLISHED, "is_featured": index < 2, "is_urgent": index in {1, 6},
                    "expires_at": timezone.now() + timedelta(days=30),
                },
            )

        seeker, _ = User.objects.get_or_create(email="seeker@example.com", defaults={"full_name": "ಅನುಷಾ", "role": User.Role.JOB_SEEKER})
        first_job = Job.objects.first()
        if first_job:
            Application.objects.get_or_create(job=first_job, applicant=seeker, defaults={"note": "ನಾನು ತಕ್ಷಣ ಕೆಲಸ ಪ್ರಾರಂಭಿಸಬಹುದು."})
        self.stdout.write(self.style.SUCCESS("Demo data ready. Employer: employer@example.com, seeker: seeker@example.com."))
