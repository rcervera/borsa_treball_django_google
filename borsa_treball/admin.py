from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuari, Sector, Empresa, FamiliaProfessional, Estudiant, Cicle,
    EstudiEstudiant, CapacitatClau, Funcio, Oferta, Candidatura,
    Noticia, RegistreAuditoria, NivellIdioma
)

class UsuariAdmin(UserAdmin):
    model = Usuari
    list_display = ('email', 'nom', 'cognoms', 'tipus', 'is_staff', 'is_active')
    list_filter = ('tipus', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informació personal', {'fields': ('nom', 'cognoms', 'telefon', 'data_naixement', 'adreca')}),
        ('Permisos', {'fields': ('tipus', 'is_staff', 'is_active', 'groups', 'user_permissions')}),
        ('Dates importants', {'fields': ('darrera_connexio',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'tipus', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('email', 'nom', 'cognoms')
    ordering = ('email',)

class EstudiEstudiantInline(admin.TabularInline):
    model = EstudiEstudiant
    extra = 1
    fields = ('cicle', 'any_inici', 'any_fi', 'centre_estudis')
    autocomplete_fields = ['cicle']
    show_change_link = True

class CandidaturaInline(admin.TabularInline):
    model = Candidatura
    extra = 0
    fields = ('oferta', 'estat', 'data_candidatura', 'puntuacio')
    readonly_fields = ('data_candidatura',)
    autocomplete_fields = ['oferta']
    show_change_link = True
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('oferta', 'oferta__empresa')

class EstudiantAdmin(admin.ModelAdmin):
    list_display = ('usuari', 'get_nom_complet', 'get_email')
    search_fields = ('usuari__email', 'usuari__nom', 'usuari__cognoms')
    raw_id_fields = ('usuari',)
    inlines = [EstudiEstudiantInline, CandidaturaInline]
    
    def get_nom_complet(self, obj):
        return obj.usuari.get_full_name()
    get_nom_complet.short_description = 'Nom complet'
    
    def get_email(self, obj):
        return obj.usuari.email
    get_email.short_description = 'Email'

class FuncioInline(admin.TabularInline):
    model = Funcio
    extra = 1
    ordering = ('ordre',)

class OfertaInline(admin.TabularInline):
    model = Oferta
    extra = 0
    fields = ('titol', 'tipus_contracte', 'jornada', 'data_limit', 'activa', 'visible')
    readonly_fields = ('data_publicacio',)
    show_change_link = True
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('empresa')

class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nom_comercial', 'cif', 'sector', 'usuari')
    search_fields = ('nom_comercial', 'cif', 'rao_social')
    list_filter = ('sector',)
    raw_id_fields = ('usuari',)
    inlines = [OfertaInline]

class CicleAdmin(admin.ModelAdmin):
    list_display = ('codi', 'nom', 'familia', 'grau', 'durada')
    search_fields = ('codi', 'nom')
    list_filter = ('familia', 'grau')
    ordering = ('familia', 'codi')


class NivellIdiomaInline(admin.TabularInline):
    model = NivellIdioma
    extra = 1

class OfertaAdmin(admin.ModelAdmin):
    list_display = ('titol', 'empresa', 'tipus_contracte', 'jornada', 'data_publicacio', 'data_limit', 'activa', 'visible')
    search_fields = ('titol', 'empresa__nom_comercial', 'descripcio')
    list_filter = ('tipus_contracte', 'jornada', 'activa', 'visible', 'data_publicacio')
    filter_horizontal = ('cicles', 'capacitats_clau')
    inlines = [FuncioInline, NivellIdiomaInline]
    date_hierarchy = 'data_publicacio'
    autocomplete_fields = ['empresa']

from django.contrib import admin
from .models import Candidatura

class CandidaturaAdmin(admin.ModelAdmin):
    list_display = ('empresa_nom', 'estudiant_nom', 'data_candidatura', 'estat')
    list_filter = ('estat', 'oferta__empresa__nom_comercial')
    search_fields = (
        'estudiant__usuari__nom',
        'estudiant__usuari__cognoms',
        'oferta__empresa__nom_comercial',
        'oferta__titol'
    )
    date_hierarchy = 'data_candidatura'
    autocomplete_fields = ['estudiant', 'oferta']
    list_per_page = 20  
    list_max_show_all = 200

    def empresa_nom(self, obj):
        return obj.oferta.empresa.nom_comercial
    empresa_nom.short_description = "Empresa"
    empresa_nom.admin_order_field = 'oferta__empresa__nom_comercial'

    def estudiant_nom(self, obj):
        return obj.estudiant.usuari.get_full_name()
    estudiant_nom.short_description = "Estudiant"
    estudiant_nom.admin_order_field = 'estudiant__usuari__nom'


class NoticiaAdmin(admin.ModelAdmin):
    list_display = ('titol', 'destinatari', 'data_publicacio', 'visible')
    search_fields = ('titol', 'descripcio')
    list_filter = ('destinatari', 'visible')
    date_hierarchy = 'data_publicacio'

class RegistreAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('accio', 'model_afectat', 'usuari', 'data', 'revisat')
    search_fields = ('accio', 'model_afectat', 'descripcio')
    list_filter = ('model_afectat', 'revisat', 'data')
    date_hierarchy = 'data'
    readonly_fields = ('data',)

admin.site.register(Usuari, UsuariAdmin)
admin.site.register(Sector)
admin.site.register(FamiliaProfessional)
admin.site.register(Empresa, EmpresaAdmin)
admin.site.register(Estudiant, EstudiantAdmin)
admin.site.register(Cicle, CicleAdmin)
admin.site.register(CapacitatClau)
admin.site.register(Oferta, OfertaAdmin)
admin.site.register(Candidatura, CandidaturaAdmin)
admin.site.register(Noticia, NoticiaAdmin)
admin.site.register(RegistreAuditoria, RegistreAuditoriaAdmin)