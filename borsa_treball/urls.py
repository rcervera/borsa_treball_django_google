from django.urls import path
from . import views
from . import views_empresa

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('', views.index, name='index'),
    path('registre/estudiant/', views.login, name='registre_estudiant'),
    path('registre/empresa/', views.registre_empresa, name='registre_empresa'),
    
    path('empresa/ofertes/', views_empresa.llista_ofertes, name='llista_ofertes_empresa'),
    path('empresa/oferta/nova/', views_empresa.afegir_oferta_directe, name='afegir_oferta'),
    path('api/empresa/oferta/nova', views_empresa.crear_oferta_api, name='afegir_oferta_api'),
    path('empresa/oferta/<int:oferta_id>/toggle-visibilitat/', views_empresa.toggle_visibilitat_oferta, name='toggle_visibilitat_oferta'),
    path('empresa/oferta/<int:oferta_id>/esborrar/', views_empresa.esborrar_oferta, name='esborrar_oferta'),
    path('empresa/oferta/<int:oferta_id>/', views_empresa.detall_oferta, name='detall_oferta'),
    path('empresa/oferta/<int:oferta_id>/editar/', views_empresa.editar_oferta, name='editar_oferta'),
     # URLs per gestió del perfil
    path('empresa/perfil/editar', views_empresa.editar_perfil_empresa, name='editar_perfil_empresa'),
    path('empresa/perfil/canviar-contrasenya/', views_empresa.api_canviar_contrasenya, name='canviar_contrasenya'),

    # altres rutes...
]