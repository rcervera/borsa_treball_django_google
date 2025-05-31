from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Usuari, Sector, Empresa, FamiliaProfessional, Estudiant, Cicle,
    EstudiEstudiant, CapacitatClau, Funcio, Oferta, Candidatura,
    Noticia, RegistreAuditoria
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

class OfertaAdmin(admin.ModelAdmin):
    list_display = ('titol', 'empresa', 'tipus_contracte', 'jornada', 'data_publicacio', 'data_limit', 'activa', 'visible')
    search_fields = ('titol', 'empresa__nom_comercial', 'descripcio')
    list_filter = ('tipus_contracte', 'jornada', 'activa', 'visible', 'data_publicacio')
    filter_horizontal = ('cicles', 'capacitats_clau')
    inlines = [FuncioInline]
    date_hierarchy = 'data_publicacio'
    autocomplete_fields = ['empresa']

class CandidaturaAdmin(admin.ModelAdmin):
    list_display = ('oferta', 'estudiant', 'estat', 'data_candidatura', 'puntuacio')
    search_fields = ('oferta__titol', 'estudiant__usuari__email')
    list_filter = ('estat', 'oferta__empresa')
    raw_id_fields = ('oferta', 'estudiant')
    date_hierarchy = 'data_candidatura'

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