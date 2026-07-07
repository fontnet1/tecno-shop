import logging

import ghasedak_sms
from tecno_shop import settings

logger = logging.getLogger(__name__)


def sms_info(request):
    """SMS account information for display in admin"""
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

    except Exception as e:
        logger.error("Ghasedak API error: %s", str(e), exc_info=True)

    return {

        "sms_balance": "-",
        "sms_plan": "-",
        "sms_expire": "-",
    }

#new folder in orginal template to admin in admin to index.html
# {% extends "admin/index.html" %}
#
# {% block content %}
#
# <div class="module">
#     <h2>اطلاعات پنل پیامک</h2>
#
#     <table style="width:100%">
#         <tr>
#             <th>اعتبار</th>
#             <td>{{ sms_balance }}</td>
#         </tr>
#
#         <tr>
#             <th>پلن</th>
#             <td>{{ sms_plan }}</td>
#         </tr>
#
#         <tr>
#             <th>تاریخ انقضا</th>
#             <td>{{ sms_expire }}</td>
#         </tr>
#     </table>
# </div>
#
# {{ block.super }}
#
# {% endblock %}