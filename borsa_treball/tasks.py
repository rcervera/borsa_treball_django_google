# la_teva_app/tasks.py
from huey.contrib.djhuey import task
from django.core.mail import send_mail

@task()
def enviar_email_async(subject, message, destinatari_list):
    send_mail(
        subject,
        message,
        'rcerver4@xtec.cat',
        destinatari_list,
        fail_silently=False,
    )