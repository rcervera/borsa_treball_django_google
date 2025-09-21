from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.timezone import now
from .models import Candidatura


@receiver(pre_save, sender=Candidatura)
def enviar_email_si_activa(sender, instance, **kwargs):
    if not instance.pk:
        return  # Nova candidatura, no comparem

    anterior = Candidatura.objects.get(pk=instance.pk)

    # Només si activa passa de False → True
    if not anterior.activa and instance.activa:
        empresa = instance.oferta.empresa

        if empresa and empresa.usuari and empresa.usuari.email:
            subject = "Nova candidatura activada"

            # Renderitzar la plantilla HTML amb context
            html_content = render_to_string(
                "borsa_treball/emails/candidatura_activada.html",
                {
                    "empresa_nom": empresa.nom_comercial,
                    "estudiant_nom": instance.estudiant.get_full_name(),
                    "oferta_nom": instance.oferta.titol,
                    "carta_presentacio": instance.carta_presentacio,
                    "any": now().year,
                },
            )

            # Versió de text pla (fallback)
            text_content = (
                f"Benvolguts/des {empresa.nom_comercial},\n\n"
                f"La candidatura de {instance.estudiant} per a l'oferta {instance.oferta} ha estat activada.\n\n"
                f"Carta de presentació:\n{instance.carta_presentacio}\n\n"
                "Trobareu adjunt el CV de l’estudiant.\n\n"
                "Atentament,\nBorsa de treball"
            )

            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,  # text pla               
                to=['rcerver4@xtec.cat']
                # to=[empresa.usuari.email],  # email de l'usuari associat a l'empresa
            )
            email.attach_alternative(html_content, "text/html")

            # Adjuntar CV si existeix
            if instance.cv_adjunt:
                email.attach_file(instance.cv_adjunt.path)

            # Adjuntar altres documents si existeixen
            if instance.altres_adjunts:
                email.attach_file(instance.altres_adjunts.path)

            email.send(fail_silently=False)
