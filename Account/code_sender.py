import ghasedak_sms
from tecno_shop import settings

sms_api = ghasedak_sms.Ghasedak(settings.GHASEDAK_API_KEY)


newotpcommand = ghasedak_sms.SendOtpInput(
    send_date=None,
    receptors=[
        ghasedak_sms.SendOtpReceptorDto(
            mobile='09*********'
        )
    ],
    template_name='Ghasedak',
    inputs=[
        ghasedak_sms.SendOtpInput.OtpInput(param='Code', value='1234'),
    ],
    udh=False
)

