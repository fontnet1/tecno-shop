import ghasedak_sms
from tecno_shop import settings

def sms_info(request):
    if not request.path.startswith("/admin/"):
        return {}

    if not request.user.is_staff:
        return {}

    try:
        sms_api = ghasedak_sms.Ghasedak(settings.GHASEDAK_API_KEY)

        response = sms_api.get_account_information()

        if response.get("isSuccess"):
            data = response.get("data", {})

            return {
                "sms_balance": data.get("credit"),
                "sms_plan": data.get("plan"),
                "sms_expire": data.get("expireDate"),
            }

    except Exception:
        print("API GASEDAK erore")

    return {
        "sms_balance": "-",
        "sms_plan": "-",
        "sms_expire": "-",
    }