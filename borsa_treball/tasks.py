# la_teva_app/tasks.py
from huey.contrib.djhuey import task, db_task
from django.core.mail import send_mail
from .models import Oferta, Estudiant
from django.template.loader import render_to_string  # <-- Importa render_to_string
from django.utils.html import strip_tags  # <-- Per crear la versió de text pla
from django.conf import settings


@task()
def enviar_email_async(subject, message, destinatari_list):
    send_mail(
        subject,
        message,
        'rcerver4@xtec.cat',
        destinatari_list,
        fail_silently=False,
    )



@db_task()
def enviar_notificacio_nova_oferta(oferta_id):
    """
    Tasca que envia un email en format HTML als estudiants els cicles dels quals
    coincideixen amb els de l'oferta.
    """
    try:
        oferta = Oferta.objects.get(id=oferta_id)
    except Oferta.DoesNotExist:
        return

    cicles_oferta_ids = oferta.cicles.values_list('id', flat=True)

    if not cicles_oferta_ids:
        return

    estudiants_a_notificar = Estudiant.objects.filter(
        estudis__cicle_id__in=cicles_oferta_ids
    ).select_related('usuari').distinct() # Usem select_related per optimitzar la consulta

    assumpte = f"Nova oferta de treball: {oferta.titol}"

    for estudiant in estudiants_a_notificar:
        # 1. Creem el context amb les dades per a la plantilla
        context = {
            'oferta': oferta,
            'estudiant': estudiant,
        }

        # 2. Renderitzem la plantilla HTML a un string
        html_missatge = render_to_string('borsa_treball/emails/oferta_activada.html', context)
        
        # 3. Creem una versió en text pla com a fallback (opcional però recomanat)
        missatge_text_pla = strip_tags(html_missatge)

        # 4. Enviem l'email amb la versió HTML
        send_mail(
            assumpte,
            missatge_text_pla,  # Versió per a clients que no llegeixen HTML
            settings.DEFAULT_FROM_EMAIL,
            ['rcerver4@xtec.cat'],#[estudiant.usuari.email],
            html_message=html_missatge,  # <-- Aquí passem l'HTML
            fail_silently=False,
        )

    print(f"S'han enviat notificacions a {estudiants_a_notificar.count()} estudiants per l'oferta '{oferta.titol}'.")
