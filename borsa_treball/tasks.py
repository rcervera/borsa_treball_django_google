# la_teva_app/tasks.py
from huey.contrib.djhuey import task
from django.core.mail import send_mail
from .models import Oferta, Estudiant
from django.template.loader import render_to_string  # <-- Importa render_to_string
from django.utils.html import strip_tags  # <-- Per crear la versió de text pla
from django.conf import settings


@task()
def enviar_email_async(subject, message, destinatari_list, html_message=None):
    """
    Envia un email asíncronament a una llista curta de destinataris (normalment un).
    """
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        destinatari_list,
        fail_silently=False,
        html_message=html_message
    )
