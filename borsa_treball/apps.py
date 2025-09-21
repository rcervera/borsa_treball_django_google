from django.apps import AppConfig


class BorsaTreballConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'borsa_treball'

    def ready(self):
        import borsa_treball.signals  # carrega els senyals
