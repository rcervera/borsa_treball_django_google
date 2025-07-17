import mimetypes
import os
from django.http import Http404, HttpResponse


# --- Funcions relacionades amb descàrregues de fitxers --- #

def resposta_descarrega_cv(candidatura):
    """
    Donada una instància de `Candidatura`, retorna una HttpResponse per descarregar el CV.
    """
    if not candidatura.cv_adjunt:
        raise Http404("CV no trobat")

    file_path = candidatura.cv_adjunt.path
    if not os.path.exists(file_path):
        raise Http404("Fitxer no trobat")

    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = 'application/octet-stream'

    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type=content_type)

    filename = generar_nom_fitxer_cv(candidatura)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


def generar_nom_fitxer_cv(candidatura):
    """
    Genera un nom de fitxer personalitzat per descarregar el CV.
    """
    nom = candidatura.estudiant.usuari.get_full_name()
    titol = candidatura.oferta.titol
    filename = f"CV_{nom}_{titol}.pdf"
    return filename.replace(' ', '_').replace(',', '')
