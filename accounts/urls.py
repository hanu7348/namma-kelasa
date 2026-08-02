from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.request_otp, name="request_otp"),
    path("verify/", views.verify_otp, name="verify_otp"),
    path("profile/", views.complete_profile, name="complete_profile"),
    path("logout/", views.logout_view, name="logout"),
]
