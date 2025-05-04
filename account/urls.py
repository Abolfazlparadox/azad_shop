# urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from account.forms import VerifiedAuthenticationForm
from .views import SignupView, VerifyEmailView, \
    UserDashboardView, RequestRoleView, AddressCreateView, AddressSetDefaultView, AddressUpdateView, \
    CustomLogoutView, ForgotPasswordView, VerifyOTPView, ResetPasswordView, ProfileSettingsView, \
    ResendVerificationView, AccountLockoutView, ChangePasswordView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/',auth_views.LoginView.as_view(authentication_form=VerifiedAuthenticationForm,template_name='account/login.html'),name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('dashboard/', UserDashboardView.as_view(), name='user_dashboard'),
    path('request-role/', RequestRoleView.as_view(), name='request_role'),
    path('address/add/', AddressCreateView.as_view(), name='address_add'),
    path('address/<int:pk>/set-default/', AddressSetDefaultView.as_view(), name='address_set_default'),
    path('address/<int:pk>/edit/', AddressUpdateView.as_view(), name='address_edit'),
    path('settings/', ProfileSettingsView.as_view(), name='profile_settings'),
    path('resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('lockout/', AccountLockoutView.as_view(), name='account_lockout'),
    path('verify-email/<int:pk>/', VerifyEmailView.as_view(), name='verify-email'),
    path('verify-email/resend/<int:pk>/', ResendVerificationView.as_view(), name='resend-verification'),

]
