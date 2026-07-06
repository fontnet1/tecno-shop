from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.core.validators import MinValueValidator, MaxValueValidator


class UserManager(BaseUserManager):

    def create_user(self , phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone is required.")

        user = self.model(
            phone=phone,
            **extra_fields
        )


        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, phone, password=None, **extra_fields):

        extra_fields.setdefault("is_admin", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(
            phone=phone,
            password=password,
            **extra_fields
        )


class User(AbstractBaseUser):
    email = models.EmailField(
        verbose_name="آدرس ایمیل",
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    phone = models.CharField(
        max_length=11,
        unique=True,
        verbose_name="شماره تلفن",
    )
    full_name = models.CharField(max_length=255,verbose_name="نام کامل")
    is_active = models.BooleanField(default=False,verbose_name="فعال")
    is_admin = models.BooleanField(default=False,verbose_name="ادمین")

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name="کاربر"
        verbose_name_plural=verbose_name+"ها"

    def __str__(self):
        return self.phone

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
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

    phone = models.CharField(max_length=11)

    code = models.PositiveIntegerField(
        validators=[
            MinValueValidator(100000),
            MaxValueValidator(999999),
        ]
    )

    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
    )

    created_at = models.DateTimeField(auto_now_add=True)