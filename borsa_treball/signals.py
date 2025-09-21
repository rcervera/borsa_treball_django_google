# borsa_treball/signals.py
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives, mail_admins
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from .models import Candidatura

logger = logging.getLogger('borsa_treball')

@receiver(post_save, sender=Candidatura)
def enviar_email_si_activa(sender, instance, created, **kwargs):
    """
    Envia un email a l'usuari de l'empresa quan una candidatura passa de activa=False a activa=True.
    Si hi ha error, envia un email als admins i registra l'error.
    """
    """
    Signal de prova: envia un email senzill a rcerver4@xtec.cat quan activa passa a True
    """
    if not created:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            if not old_instance.activa and instance.activa:
                subject = "Prova d'email: Candidatura activada"
                message = f"La candidatura {instance.pk} de l'estudiant {instance.estudiant.get_full_name()} s'ha activat."
                from_email = settings.DEFAULT_FROM_EMAIL
                to = ['rcerver4@xtec.cat']

                send_mail(subject, message, from_email, to)
                logger.info(f"Email de prova enviat per candidatura {instance.pk}")
        except Exception as e:
            error_msg = f"Error enviant email de prova per candidatura {instance.pk}: {e}"
            logger.error(error_msg)
            mail_admins(subject="Error enviant email de prova", message=error_msg)