import logging
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives, mail_admins
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from .models import Candidatura

logger = logging.getLogger('borsa_treball')

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import Oferta


@receiver(post_save, sender=Oferta)
def enviar_email_nova_oferta(sender, instance, created, **kwargs):
    """
    Envia un email quan es crea una nova oferta (no quan s'actualitza).
    """
    if created:  # només si s'ha creat
        subject = f"Nova oferta: {instance.titol}"
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [settings.EMAIL_RESPONSABLE_BORSA,'rcerver4@xtec.cat']


        # Renderitzar plantilla HTML
        url_login = f"{settings.SITE_URL}{reverse('login')}"  # assegura que tens SITE_URL a settings.py  
        html_content = render_to_string(
            "borsa_treball/emails/nova_oferta.html",
            {"oferta": instance, "url_login": url_login},
        )

        # fallback text pla
        text_content = f"S'ha publicat una nova oferta: {instance.titol}"

        msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
        msg.attach_alternative(html_content, "text/html")
        msg.send()




@receiver(pre_save, sender=Candidatura)
def enviar_email_si_activa(sender, instance, **kwargs):
    """
    Envia un email a l'usuari de l'empresa quan una candidatura passa de activa=False a activa=True.
    Fa servir la plantilla HTML i adjunta el CV si existeix.
    Si hi ha error, envia un email als admins i registra l'error.
    """
    if instance.pk:  # només si ja existia
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            if not old_instance.activa and instance.activa:
                empresa = instance.oferta.empresa
                usuari_empresa = empresa.usuari

                if usuari_empresa and usuari_empresa.email:
                    subject = f"Nova candidatura activada per a {empresa.nom_comercial}"
                    from_email = settings.DEFAULT_FROM_EMAIL
                    # to = ['rcerver4@xtec.cat']
                    to = [usuari_empresa.email, 'rcerver4@xtec.cat' ]

                    # Generar URL absoluta del login
                    url_login = f"{settings.SITE_URL}{reverse('login')}"  # assegura que tens SITE_URL a settings.py  

                    # Renderitzar la plantilla HTML
                    html_content = render_to_string(
                        "borsa_treball/emails/candidatura_activada.html",
                        {
                            "empresa": empresa,
                            "candidatura": instance,
                            "estudiant": instance.estudiant.usuari,
                            "url_login": url_login,
                            "any": instance.data_canvi_estat.year,
                        },
                    )

                    # Fallback de text pla
                    text_content = f"""
                        Benvolguts/des {empresa.nom_comercial},

                        S'ha activat una nova candidatura per a l'oferta {instance.oferta}.

                        Carta de presentació:
                        {instance.carta_presentacio}

                        Podeu visualitzar totes les candidatures a les vostres ofertes iniciant sessió a la web:
                        {url_login}

                        Missatge automàtic enviat des de l'app de la Borsa de Treball de l'Institut Vidal i Barraquer.
                    """

                    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
                    msg.attach_alternative(html_content, "text/html")

                    # Adjuntar CV si existeix
                    if instance.cv_adjunt:
                        try:
                            msg.attach_file(instance.cv_adjunt.path)
                        except Exception as e:
                            logger.warning(f"No s'ha pogut adjuntar el CV de la candidatura {instance.pk}: {e}")

                    msg.send()

        except Exception as e:
            error_msg = f"Error enviant email per candidatura {instance.pk}: {e}"
            logger.error(error_msg)
            mail_admins(subject="Error enviant email de candidatura", message=error_msg)
