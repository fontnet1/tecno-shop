class AccountSettings:
    """Account module settings"""

    # OTP
    OTP_EXPIRE_MINUTES: int = 2
    OTP_CODE_LENGTH: int = 6
    OTP_MAX_RESEND_ATTEMPTS: int = 3
    OTP_MAX_VERIFY_ATTEMPTS: int = 5
    OTP_RESEND_WINDOW_SECONDS: int = 120
    OTP_VERIFY_WINDOW_SECONDS: int = 300

    # SMS
    SMS_TEMPLATE_NAME: str = "Ghasedak"

    # Password
    PASSWORD_MIN_LENGTH: int = 8