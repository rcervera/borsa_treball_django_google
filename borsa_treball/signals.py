import logging
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Candidatura

logger = logging.getLogger('borsa_treball')

@receiver(pre_save, sender=Candidatura)
def enviar_email_si_activa(sender, instance, **kwargs):
    """
    Signal de prova: envia un email senzill a rcerver4@xtec.cat
    quan el camp activa passa de False a True.
    """
    # només si l'objecte ja existeix (no és una creació)
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            # comprovem el canvi d'estat
            if not old_instance.activa and instance.activa:
                subject = "Prova d'email: Candidatura activada"
                message = (
                    f"La candidatura {instance.pk} "
                    f"de l'estudiant {instance.estudiant.usuari.get_full_name()} "
                    f"s'ha activat."
                )
                to = ['rcerver4@xtec.cat']

                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, to)

        except Exception as e:
            error_msg = f"Error enviant email de prova per candidatura {instance.pk}: {e}"
            logger.error(error_msg)
