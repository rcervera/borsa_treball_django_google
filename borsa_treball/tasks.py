# la_teva_app/tasks.py
import logging
from huey.contrib.djhuey import task
from django.core.mail import send_mail
from .models import Oferta, Estudiant
from django.template.loader import render_to_string  # <-- Importa render_to_string
from django.utils.html import strip_tags  # <-- Per crear la versió de text pla
from django.conf import settings

logger = logging.getLogger(__name__)

from django.core.mail import EmailMultiAlternatives

@task()
def enviar_email_async(subject, message, destinatari_list, html_message, bcc_list):
    """
    Envia un email asíncronament amb possibilitat de BCC.
    """
    try:
        if bcc_list is None:
            bcc_list = []

        destinatari_str = ', '.join(destinatari_list)
        bcc_str = ', '.join(bcc_list)
        logger.info(f"Enviant correu a: {destinatari_str} BCC: {bcc_str}")

        email = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinatari_list,
            bcc=bcc_list
        )

        if html_message:
            email.attach_alternative(html_message, "text/html")

        email.send(fail_silently=False)

        logger.info(f"Email enviat correctament a: {destinatari_str}")

    except Exception as e:
        logger.error(f"Error enviant email: {e}")
