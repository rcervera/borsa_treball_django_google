# borsa_treball/signals.py
import logging
from time import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives, mail_admins
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from .models import Candidatura, RegistreAuditoria

logger = logging.getLogger('borsa_treball')

@receiver(post_save, sender=Candidatura)
def enviar_email_si_activa(sender, instance, created, **kwargs):
    """
    Envia un email a l'usuari de l'empresa quan una candidatura passa de activa=False a activa=True.
    Si hi ha error, envia un email als admins i registra l'error.
    """
     # ---- Registrar acció a RegistreAuditoria ----
    from django.contrib.auth import get_user_model
    Usuari = get_user_model()
    RegistreAuditoria.objects.create(
                    accio="Activació Candidatura",
                    model_afectat="Candidatura",
                    descripcio=f"Candidatura {instance.pk} activada per l'estudiant {instance.estudiant.get_full_name()} a l'oferta {instance.oferta}.",
                    usuari=None,  # Opcional: si vols, posa l'usuari actual si tens request
                    data=timezone.now(),
                    revisat=False
                )