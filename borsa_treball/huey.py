from huey import RedisHuey
from django.conf import settings

# Crear la instància Huey basant-nos en la configuració del settings.py
huey = RedisHuey(
    name=settings.HUEY.get('name', 'borsa_treball'),
    host=settings.HUEY.get('host', '127.0.0.1'),
    port=settings.HUEY.get('port', 6379),
    db=settings.HUEY.get('db', 0)
)
