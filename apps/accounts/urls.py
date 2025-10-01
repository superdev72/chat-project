from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.UserRegistrationView.as_view(), name="user-register"),
    path("login/", views.login_view, name="user-login"),
    path("logout/", views.logout_view, name="user-logout"),
    path("profile/", views.profile_view, name="user-profile"),
    path("verify-email/<str:token>/", views.verify_email_view, name="verify-email"),
    path(
        "resend-verification/",
        views.resend_verification_email_view,
        name="resend-verification",
    ),
]
