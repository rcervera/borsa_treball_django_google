# borsa_treball/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from .models import Candidatura

@receiver(post_save, sender=Candidatura)
def enviar_email_si_activa(sender, instance, created, **kwargs):
    """
    Envia un email a l'usuari de l'empresa quan una candidatura passa de activa=False a activa=True
    """
    if not created:  # només si ja existia
        # recuperar l'estat anterior
        old_instance = sender.objects.get(pk=instance.pk)
        if not old_instance.activa and instance.activa:
            empresa = instance.oferta.empresa
            usuari_empresa = empresa.usuari

            if usuari_empresa and usuari_empresa.email:
                subject = f"Nova candidatura activada per a {empresa.nom_comercial}"
                from_email = settings.DEFAULT_FROM_EMAIL
                #to = [usuari_empresa.email]
                to = 'rcerver4@xtec.cat'

                # Generar URL absoluta del login
                url_login = f"{reverse('login')}"

                # renderitzar la plantilla HTML
                html_content = render_to_string(
                    "borsa_treball/emails/candidatura_activada.html",
                    {
                        "empresa": empresa,
                        "candidatura": instance,
                        "estudiant": instance.estudiant,
                        "url_login": url_login,
                        "any": instance.data_canvi_estat.year,
                    },
                )

                # fallback de text pla
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

                # adjuntar CV si existeix
                if instance.cv_adjunt:
                    msg.attach_file(instance.cv_adjunt.path)

                

                msg.send()
