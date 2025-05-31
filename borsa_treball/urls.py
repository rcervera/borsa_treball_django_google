from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('', views.index, name='index'),
    path('accounts/registre/estudiant/', views.login, name='registre_estudiant'),
    path('accounts/registre/empresa/', views.login, name='registre_empresa'),
   
    # altres rutes...
]