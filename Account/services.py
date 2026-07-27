import logging
from typing import Optional
import secrets
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

import ghasedak_sms
from tecno_shop import settings

from .models import User, OTP
from .conf import AccountSettings

logger = logging.getLogger(__name__)


def _get_sms_api():
    """Create a lazy SMS API instance"""
    if not hasattr(settings, "_sms_api"):
        settings._sms_api = ghasedak_sms.Ghasedak(settings.GHASEDAK_API_KEY)
    return settings._sms_api


class OTPService:
    """OTP code management service"""

    @staticmethod
    def _generate_and_store_otp(phone: str, purpose: str) -> tuple:
        """Generate OTP code, hash it, store in DB, and return (otp_object, raw_code).

        Args:
            phone: User's phone number (used as identifier in DB)
            purpose: Purpose of sending the code (register, login, reset_password)

        Returns:
            tuple: (OTP instance, raw_code as int)

        Raises:
            ValueError: If send rate limit has been exceeded
        """
        # ─── Rate Limiting: Max 3 times in 2 minutes ───
        cache_key = f"otp_resend_{phone}_{purpose}"
        attempt_count = cache.get(cache_key, 0)

        if attempt_count >= AccountSettings.OTP_MAX_RESEND_ATTEMPTS:
            logger.warning("OTP resend rate limit exceeded for %s", phone)
            raise ValueError(
                "Too many requests. Please wait 2 minutes."
            )

        code = secrets.randbelow(900000) + 100000

        OTP.objects.filter(
            phone=phone,
            purpose=purpose,
        ).delete()

        otp = OTP.objects.create(
            phone=phone,
            purpose=purpose,
        )
        otp.set_code(code)
        otp.save(update_fields=["code_hash"])

        # ─── Rate limit counter ───
        cache.set(cache_key, attempt_count + 1, timeout=AccountSettings.OTP_RESEND_WINDOW_SECONDS)

        logger.info("OTP generated for %s for purpose: %s", phone, purpose)

        return otp, code

    @staticmethod
    def send_otp_sms(phone: str, purpose: str) -> OTP:
        """Generate OTP and send via SMS (Ghasedak).

        Args:
            phone: User's 11-digit phone number
            purpose: Purpose of sending the code

        Returns:
            OTP: Created OTP model instance

        Raises:
            ValueError: If send rate limit has been exceeded
        """
        otp, code = OTPService._generate_and_store_otp(phone, purpose)
        print(code)

        # ─── Send SMS via Ghasedak ───
        sms = ghasedak_sms.SendOtpInput(
            send_date=None,
            receptors=[
                ghasedak_sms.SendOtpReceptorDto(
                    mobile=phone,
                )
            ],
            template_name=AccountSettings.SMS_TEMPLATE_NAME,
            inputs=[
                ghasedak_sms.SendOtpInput.OtpInput(
                    param="Code",
                    value=str(code),
                ),
            ],
            udh=False,
        )

        # sms_api.send_otp(sms)  # ← Enable in production

        logger.info("OTP sent via SMS to %s for purpose: %s", phone, purpose)
        return otp

    @staticmethod
    def send_otp_email(email: str, phone: str, purpose: str) -> OTP:
        """Generate OTP and send via Email.

        Args:
            email: User's email address
            phone: User's phone number (used as DB identifier)
            purpose: Purpose of sending the code

        Returns:
            OTP: Created OTP model instance

        Raises:
            ValueError: If send rate limit has been exceeded
        """
        from django.core.mail import send_mail
        from django.conf import settings

        otp, code = OTPService._generate_and_store_otp(phone, purpose)

        subject_map = {
            OTP.REGISTER: "Verify Your Registration",
            OTP.LOGIN: "Login Verification Code",
            OTP.RESET_PASSWORD: "Password Reset Code",
        }
        subject = subject_map.get(purpose, "Verification Code")

        message = (
            f"Hello,\n\n"
            f"Your verification code is: {code}\n\n"
            f"This code expires in {AccountSettings.OTP_EXPIRE_MINUTES} minutes.\n"
            f"If you did not request this, please ignore this email."
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        logger.info("OTP sent via Email to %s for purpose: %s", email, purpose)

        return otp

    @staticmethod
    def send_otp(phone: str, purpose: str, email: str = None) -> OTP:
        """Send OTP via Email if email provided, otherwise via SMS.

        Args:
            phone: User's phone number
            purpose: Purpose of sending the code
            email: User's email address (optional, if provided sends via email)

        Returns:
            OTP: Created OTP model instance

        Raises:
            ValueError: If send rate limit has been exceeded
        """
        if email:
            return OTPService.send_otp_email(
                email=email,
                phone=phone,
                purpose=purpose,
            )
        return OTPService.send_otp_sms(phone, purpose)

    @staticmethod
    def verify_otp(phone: str, code: str, purpose: str) -> Optional[OTP]:
        """Verify an OTP code.

        Args:
            phone: User's phone number
            code: Entered code
            purpose: Purpose of sending the code

        Returns:
            OTP: Valid OTP instance or None

        Raises:
            ValueError: If verify rate limit has been exceeded
        """
        # ─── Rate Limiting: Max 5 times in 5 minutes ───
        cache_key = f"otp_verify_{phone}"
        verify_attempts = cache.get(cache_key, 0)

        if verify_attempts >= AccountSettings.OTP_MAX_VERIFY_ATTEMPTS:
            logger.warning("OTP verify rate limit exceeded for %s", phone)
            raise ValueError(
                "Too many attempts. Please wait 5 minutes."
            )

        otps = OTP.objects.filter(
            phone=phone,
            purpose=purpose,
            created_at__gte=timezone.now() - timedelta(
                minutes=AccountSettings.OTP_EXPIRE_MINUTES
            ),
        )

        for otp_obj in otps:
            if otp_obj.verify_code(code):
                # Success → Clear counter
                cache.delete(cache_key)
                logger.info("OTP verified for %s", phone)
                return otp_obj

        # Failure → Increment counter
        cache.set(cache_key, verify_attempts + 1, timeout=AccountSettings.OTP_VERIFY_WINDOW_SECONDS)
        logger.warning("Invalid OTP attempt for %s", phone)
        return None

class AuthService:
    """Authentication and user management service"""

    @staticmethod
    @transaction.atomic
    def register_user(
        phone: str,
        full_name: str,
        email: Optional[str],
        password: str,
    ) -> User:
        """Register a new user.

        Args:
            phone: Phone number
            full_name: Full name
            email: Email (optional)
            password: Password

        Returns:
            User: Created user
        """
        user = User.objects.create_user(
            phone=phone,
            full_name=full_name,
            email=email or "",
            password=password,
            is_active=False,
        )
        logger.info("New user registered: %s", phone)
        return user

    @staticmethod
    def reset_password(user_id: int, new_password: str) -> None:
        """Reset user password.

        Args:
            user_id: User ID
            new_password: New password
        """
        user = User.objects.get(id=user_id)
        user.set_password(new_password)
        user.save()
        logger.info("Password reset for user: %s", user.phone)