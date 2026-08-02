from django.urls import path

from . import views

app_name = "jobs"

urlpatterns = [
    path("", views.home, name="home"),
    path("jobs/", views.job_list, name="list"),
    path("jobs/post/", views.job_create, name="create"),
    path("jobs/<uuid:public_id>/", views.job_detail, name="detail"),
    path("jobs/<uuid:public_id>/edit/", views.job_update, name="update"),
    path("jobs/<uuid:public_id>/close/", views.job_close, name="close"),
    path("jobs/<uuid:public_id>/apply/", views.apply, name="apply"),
    path("jobs/<uuid:public_id>/applicants/", views.applicants, name="applicants"),
    path("jobs/<uuid:public_id>/report/", views.report_job, name="report"),
    path("applications/<int:pk>/status/", views.application_status, name="application_status"),
    path("applications/<int:pk>/resume/", views.download_resume, name="download_resume"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("employer/profile/", views.employer_profile, name="employer_profile"),
    path("plans/", views.plans, name="plans"),
    path("plans/<str:plan>/buy/", views.purchase_plan, name="purchase_plan"),
    path("payments/success/", views.payment_success, name="payment_success"),
    path("payments/webhook/razorpay/", views.razorpay_webhook, name="razorpay_webhook"),
    path("language/<str:lang>/", views.set_language, name="set_language"),
    path("<str:page>/", views.static_page, name="static_page"),
]
