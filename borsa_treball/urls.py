from django.urls import path
from . import views
from . import views_empresa
from . import views_estudiant
from django.views.generic import TemplateView

urlpatterns = [
    path('landing', TemplateView.as_view(template_name='landing.html'), name='landing'),
    path('login/', views.login_view, name='login'),
    path('', views.index, name='index'),
    path('registre/estudiant/', views.mostrar_registre_estudiant, name='registre_estudiant'),
    #path('registre/empresa/', views.registre_empresa, name='registre_empresa'),
    path('registre/empresa/', views.mostrar_registre_empresa, name='registre_empresa'),
    path('api/registre-empresa/', views.registre_empresa, name='registre_empresa_api'),
    path('api/registre-estudiant/', views.registre_estudiant, name='registre_estudiant_api'),
    
    path('empresa/ofertes/', views_empresa.llista_ofertes, name='llista_ofertes_empresa'),
    path('empresa/oferta/nova/', views_empresa.afegir_oferta, name='afegir_oferta'),
    path('api/empresa/oferta/nova', views_empresa.crear_oferta_api, name='afegir_oferta_api'),
    path('api/empresa/oferta/<int:oferta_id>/', views_empresa.api_actualitzar_oferta, name='api_actualitzar_oferta'),
    path('empresa/oferta/<int:oferta_id>/toggle-visibilitat/', views_empresa.toggle_visibilitat_oferta, name='toggle_visibilitat_oferta'),
    path('empresa/oferta/<int:oferta_id>/esborrar/', views_empresa.esborrar_oferta, name='esborrar_oferta'),
    # path('empresa/oferta/<int:oferta_id>/', views_empresa.detall_oferta, name='detall_oferta'),
    path('empresa/oferta/<int:oferta_id>/editar/', views_empresa.editar_oferta, name='editar_oferta'),
     # URLs per gestió del perfil
    path('empresa/perfil/editar', views_empresa.editar_perfil_empresa, name='editar_perfil_empresa'),
    path('empresa/perfil/canviar-contrasenya/', views_empresa.api_canviar_contrasenya, name='canviar_contrasenya'),

     # URL API per actualitzar la informació de l'empresa
    path('api/perfil/empresa/editar/', views_empresa.api_editar_perfil_empresa, name='api_editar_perfil_empresa'),

    # URL API per actualitzar la informació del contacte (usuari)
    path('api/perfil/usuari/editar/', views_empresa.api_editar_perfil_usuari, name='api_editar_perfil_usuari'),

    # URL API per canviar la contrasenya de l'usuari
    path('api/canviar-contrasenya-empresa/', views_empresa.api_canviar_contrasenya, name='canviar_contrasenya_empresa'),

    # URL per eliminar el perfil de l'empresa (si existeix aquesta funcionalitat)
    # Assegura't de tenir la vista 'eliminar_perfil_empresa' definida al teu views.py
    path('perfil/empresa/eliminar/', views_empresa.eliminar_perfil_empresa, name='eliminar_perfil_empresa'),

    # Si tens una URL per al llistat d'ofertes de l'empresa a la qual es redirigeix
    # path('ofertes/empresa/', views.llista_ofertes_empresa, name='llista_ofertes_empresa'),


    path('tauler_ofertes', views_estudiant.llista_ofertes_estudiants, name='tauler_ofertes'),
    path('detall_oferta_tauler/<int:oferta_id>', views_estudiant.detall_oferta_tauler, name='detall_oferta_tauler'),
    
    # rutes incorrectes de moment...
    path('tauler_ofertes', views_estudiant.llista_ofertes_estudiants, name='llista_ofertes_estudiants'),
    path('estudiant/candidatures', views_estudiant.llista_candidatures_estudiant, name='llista_candidatures_estudiant'),

    path('perfil/estudiant/', views_estudiant.perfil_estudiant, name='perfil_estudiant'),
    path('api/perfil/estudiant/actualitzar/', views_estudiant.api_actualitzar_perfil_estudiant, name='api_actualitzar_perfil_estudiant'),
    path('api/perfil/estudiant/estudis/afegir/', views_estudiant.api_afegir_estudi_estudiant, name='api_afegir_estudi_estudiant'),
    path('api/perfil/estudiant/estudis/<int:estudi_id>/esborrar/', views_estudiant.api_esborrar_estudi_estudiant, name='api_esborrar_estudi_estudiant'),
     
    path('estudiant/ofertes/', views_estudiant.llista_ofertes_estudiants_auth, name='llista_ofertes_estudiant'),
    path('estudiant/ofertes/<int:oferta_id>/', views_estudiant.detall_oferta_estudiant, name='detall_oferta_estudiant'),
    path('estudiant/ofertes/<int:oferta_id>/candidatura/', views_estudiant.afegir_candidatura, name='afegir_candidatura'),
    path('estudiant/candidatures/<int:candidatura_id>/editar/', views_estudiant.editar_candidatura_estudiant, name='editar_candidatura_estudiant'),
    path('estudiant/candidatura/cv/<int:candidatura_id>', views_estudiant.descarregar_cv_candidatura, name='descarregar_cv_candidatura'),
    path('api/candidatures/<int:candidatura_id>/edit/', views_estudiant.editar_candidatura_api, name='editar_candidatura_api'),
    path('candidatures/<int:candidatura_id>/eliminar_api/', views_estudiant.eliminar_candidatura_api, name='eliminar_candidatura_api'),

    path('ofertes/<int:oferta_id>/candidatures/', views_empresa.candidatures_oferta, name='llista_candidatures_oferta'),
    path('candidatures/<int:candidatura_id>/carta/',views_empresa.veure_carta_presentacio, name='veure_carta_presentacio'),
    path('candidatures/<int:candidatura_id>/cv/', views_empresa.descarregar_cv_candidatura, name='descarregar_cv_candidatura'),
    path('candidatures/<int:candidatura_id>/canviar-estat/', views_empresa.canviar_estat_candidatura, name='canviar_estat_candidatura'),
]