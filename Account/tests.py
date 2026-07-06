from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache

from Account.models import User, OTP


class UserModelTest(TestCase):
    """User model tests"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09123456789",
            full_name="Ali Mohammadi",
            password="TestPass123!",
            is_active=True,
        )

    def test_create_user(self):
        self.assertEqual(self.user.phone, "09123456789")
        self.assertEqual(self.user.full_name, "Ali Mohammadi")
        self.assertTrue(self.user.check_password("TestPass123!"))
        self.assertFalse(self.user.is_admin)

    def test_user_string_representation(self):
        self.assertEqual(str(self.user), "09123456789")

    def test_has_perm_returns_false_for_normal_user(self):
        self.assertFalse(self.user.has_perm("any_perm"))

    def test_has_module_perms_returns_false_for_normal_user(self):
        self.assertFalse(self.user.has_module_perms("any_app"))

    def test_has_perm_returns_true_for_admin(self):
        self.user.is_admin = True
        self.user.save()
        self.assertTrue(self.user.has_perm("any_perm"))
        self.assertTrue(self.user.has_module_perms("any_app"))

    def test_is_staff_only_for_admin(self):
        self.assertFalse(self.user.is_staff)
        self.user.is_admin = True
        self.user.save()
        self.assertTrue(self.user.is_staff)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            phone="09999999999",
            full_name="Admin User",
            password="AdminPass123!",
        )
        self.assertTrue(admin.is_admin)
        self.assertTrue(admin.is_active)


class OTPModelTest(TestCase):
    """OTP model tests"""

    def test_set_and_verify_code(self):
        otp = OTP.objects.create(
            phone="09123456789",
            purpose=OTP.REGISTER,
        )
        otp.set_code(123456)
        otp.save()

        self.assertTrue(otp.verify_code(123456))
        self.assertFalse(otp.verify_code(654321))

    def test_different_codes(self):
        otp = OTP.objects.create(
            phone="09123456789",
            purpose=OTP.REGISTER,
        )
        otp.set_code(999999)
        otp.save()

        self.assertTrue(otp.verify_code(999999))
        self.assertFalse(otp.verify_code(123456))
        self.assertFalse(otp.verify_code(100000))

    def test_otp_string_representation(self):
        otp = OTP.objects.create(
            phone="09123456789",
            purpose=OTP.REGISTER,
        )
        otp.set_code(123456)
        otp.save()
        self.assertIn("09123456789", str(otp))
        self.assertIn("Register", str(otp))


class RegisterViewTest(TestCase):
    """Register view tests"""

    def test_register_page_loads(self):
        response = self.client.get(reverse("Account:register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Account")

    def test_register_valid_data(self):
        response = self.client.post(reverse("Account:register"), {
            "full_name": "Ali Mohammadi",
            "email": "ali@test.com",
            "phone": "09123456789",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
            "agree": "on",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            User.objects.filter(phone="09123456789").exists()
        )

    def test_register_duplicate_phone(self):
        User.objects.create_user(
            phone="09123456789",
            full_name="Test User",
            password="TestPass123!",
        )
        response = self.client.post(reverse("Account:register"), {
            "full_name": "Ali",
            "phone": "09123456789",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
            "agree": "on",
        })
        self.assertContains(response, "already")

    def test_register_password_mismatch(self):
        response = self.client.post(reverse("Account:register"), {
            "full_name": "Ali",
            "phone": "09999999999",
            "password": "TestPass123!",
            "confirm_password": "WrongPass!",
            "agree": "on",
        })
        self.assertContains(response, "match")

    def test_register_invalid_phone_format(self):
        response = self.client.post(reverse("Account:register"), {
            "full_name": "Ali",
            "phone": "12345678901",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
            "agree": "on",
        })
        self.assertContains(response, "09")

    def test_register_weak_password(self):
        response = self.client.post(reverse("Account:register"), {
            "full_name": "Ali",
            "phone": "09999999999",
            "password": "weak",
            "confirm_password": "weak",
            "agree": "on",
        })
        self.assertEqual(response.status_code, 200)

    def test_register_without_agree(self):
        response = self.client.post(reverse("Account:register"), {
            "full_name": "Ali",
            "phone": "09999999999",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        })
        self.assertEqual(response.status_code, 200)


class LoginViewTest(TestCase):
    """Login view tests"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone="09123456789",
            full_name="Ali",
            password="TestPass123!",
            is_active=True,
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse("Account:login"))
        self.assertEqual(response.status_code, 200)

    def test_login_valid_credentials(self):
        response = self.client.post(reverse("Account:login"), {
            "phone": "09123456789",
            "password": "TestPass123!",
        })
        self.assertEqual(response.status_code, 302)

    def test_login_invalid_password(self):
        response = self.client.post(reverse("Account:login"), {
            "phone": "09123456789",
            "password": "WrongPass!",
        })
        self.assertContains(response, "incorrect")

    def test_login_invalid_phone_format(self):
        response = self.client.post(reverse("Account:login"), {
            "phone": "123",
            "password": "TestPass123!",
        })
        self.assertContains(response, "09")

    def test_authenticated_user_redirects(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("Account:login"))
        self.assertEqual(response.status_code, 302)


class OTPVerificationTest(TestCase):
    """OTP service tests"""

    def setUp(self):
        cache.clear()

    def test_set_and_verify_otp_code(self):
        otp = OTP.objects.create(
            phone="09123456789",
            purpose=OTP.REGISTER,
        )
        otp.set_code(555555)
        otp.save()

        self.assertTrue(otp.verify_code(555555))
        self.assertFalse(otp.verify_code(123456))

    def test_user_not_created_active(self):
        """New user should not be active until OTP is verified"""
        response = self.client.post(reverse("Account:register"), {
            "full_name": "Ali",
            "phone": "09111111111",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
            "agree": "on",
        })
        user = User.objects.get(phone="09111111111")
        self.assertFalse(user.is_active)