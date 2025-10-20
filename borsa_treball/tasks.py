# la_teva_app/tasks.py
import logging
from huey.contrib.djhuey import task
from django.core.mail import send_mail
from .models import Oferta, Estudiant
from django.template.loader import render_to_string  # <-- Importa render_to_string
from django.utils.html import strip_tags  # <-- Per crear la versió de text pla
from django.conf import settings

logger = logging.getLogger(__name__)

@task()
def enviar_email_async(subject, message, destinatari_list, html_message, bcc_list=[]):
    """
    Envia un email asíncronament a una llista curta de destinataris (normalment un).
    Permet opcionalment BCC per enviar a més persones sense que es vegin entre elles.
    """
    try:
        destinatari_str = ', '.join(destinatari_list)  # converteix la llista a string llegible
        bcc_str = ', '.join(bcc_list)
        logger.info(f"Enviant correu a: {destinatari_str} BCC: {bcc_str}")
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            destinatari_list,
            fail_silently=False,
            html_message=html_message,
            bcc=bcc_list
        )
        
        logger.info(f"Email enviat correctament a: {destinatari_str}")
        
    except Exception as e:
        logger.error(f"Error enviant email: {e}")