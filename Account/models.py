from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import MinValueValidator, MaxValueValidator


class UserManager(BaseUserManager):

    def create_user(self, phone: str, password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone is required.")

        user = self.model(
            phone=phone,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, phone: str, password=None, **extra_fields):

        extra_fields.setdefault("is_admin", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(
            phone=phone,
            password=password,
            **extra_fields
        )


class User(AbstractBaseUser):
    email = models.EmailField(
        verbose_name="Email Address",
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    phone = models.CharField(
        max_length=11,
        unique=True,
        verbose_name="Phone Number",
    )
    full_name = models.CharField(max_length=255, verbose_name="Full Name")
    is_active = models.BooleanField(default=False, verbose_name="Active")
    is_admin = models.BooleanField(default=False, verbose_name="Admin")

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.phone

    def has_perm(self, perm: str, obj=None) -> bool:
        """Does the user have a specific permission?"""
        if self.is_admin:
            return True
        return False

    def has_module_perms(self, app_label: str) -> bool:
        """Does the user have access to a specific module?"""
        if self.is_admin:
            return True
        return False

    @property
    def is_staff(self) -> bool:
        """Is the user a member of the management team?"""
        return self.is_admin


class OTP(models.Model):

    REGISTER = "register"
    LOGIN = "login"
    RESET_PASSWORD = "reset_password"

    PURPOSE_CHOICES = [
        (REGISTER, "Register"),
        (LOGIN, "Login"),
        (RESET_PASSWORD, "Reset Password"),
    ]

    phone = models.CharField(max_length=11, verbose_name="Phone Number")
    code_hash = models.CharField(max_length=255, verbose_name="Code Hash")

    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        verbose_name="Purpose",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Verification Code"
        verbose_name_plural = "Verification Codes"

    def set_code(self, code: int) -> None:
        """Hash and store the OTP code"""
        self.code_hash = make_password(str(code))

    def verify_code(self, code: int) -> bool:
        """Verify the OTP code"""
        return check_password(str(code), self.code_hash)

    def __str__(self):
        return f"{self.phone} - {self.get_purpose_display()}"