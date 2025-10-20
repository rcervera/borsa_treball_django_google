from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponseRedirect
from django.urls import path, reverse

from config import settings
from .models import (
    CapacitatOferta, Usuari, Sector, Empresa, FamiliaProfessional, Estudiant, Cicle,
    EstudiEstudiant, CapacitatClau, Funcio, Oferta, Candidatura,
    Noticia, RegistreAuditoria, NivellIdioma
)

from django.utils.html import format_html 
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .tasks import enviar_email_async

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


# --- FILTRE 1: Per família professional ---
class FamiliaProfessionalFilter(admin.SimpleListFilter):
    title = 'Família professional'
    parameter_name = 'familia_professional'

    def lookups(self, request, model_admin):
        # Mostra totes les famílies com a opcions del filtre
        return [(f.id, f.nom) for f in FamiliaProfessional.objects.all()]

    def queryset(self, request, queryset):
        # Filtra estudiants segons la família professional dels seus cicles
        if self.value():
            return queryset.filter(estudis__cicle__familia__id=self.value()).distinct()
        return queryset


# --- FILTRE 2: Per cicle concret ---
class EstudiPerCicleFilter(admin.SimpleListFilter):
    title = 'Cicle (Estudi)'
    parameter_name = 'cicle'

    def lookups(self, request, model_admin):
        # Mostra tots els cicles disponibles com a opcions del filtre
        return [(c.id, c.nom) for c in Cicle.objects.all()]

    def queryset(self, request, queryset):
        # Filtra els estudiants que tenen relació amb el cicle seleccionat
        if self.value():
            return queryset.filter(estudis__cicle__id=self.value()).distinct()
        return queryset


class EstudiantAdmin(admin.ModelAdmin):    
    list_display = ('usuari', 'get_nom_complet', 'get_email', 'get_estudis')
    search_fields = ('usuari__email', 'usuari__nom', 'usuari__cognoms')
    raw_id_fields = ('usuari',)
    list_filter = (FamiliaProfessionalFilter, EstudiPerCicleFilter,)
    inlines = [EstudiEstudiantInline, CandidaturaInline]
    
    def get_nom_complet(self, obj):
        return obj.usuari.get_full_name()
    get_nom_complet.short_description = 'Nom complet'
    
    def get_email(self, obj):
        return obj.usuari.email
    get_email.short_description = 'Email'

    def get_estudis(self, obj):
        # Obtenim tots els cicles associats a l'estudiant
        cicles = [ee.cicle.nom for ee in obj.estudis.select_related('cicle').all()]
        return ", ".join(cicles) if cicles else "—"
    get_estudis.short_description = 'Estudis (Cicles)'

class FuncioInline(admin.TabularInline):
    model = Funcio
    extra = 1
    ordering = ('ordre',)

class CapacitatOfertaInline(admin.TabularInline): 
    model = CapacitatOferta
    extra = 1  # Quantes files buides apareixen per defecte

class OfertaInline(admin.TabularInline):
    model = Oferta
    extra = 0
    fields = ('titol', 'tipus_contracte', 'jornada', 'data_limit', 'data_publicacio', 'estat')
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

    # Especifiquem la nostra plantilla personalitzada per a la pàgina d'edició.
    change_form_template = "borsa_treball/admin/oferta/change_form.html"

    list_display = (
        'titol', 'empresa', 'estat_colored',
        'data_publicacio', 'data_limit', 'descripcio_curta'
    )
    search_fields = ('titol', 'empresa__nom_comercial', 'descripcio')
    list_filter = ('tipus_contracte', 'jornada', 'estat', 'data_publicacio')
    filter_horizontal = ('cicles', )
    inlines = [
        FuncioInline,
        NivellIdiomaInline,
        CapacitatOfertaInline,
        CandidaturaInline
    ]

    date_hierarchy = 'data_publicacio'
    autocomplete_fields = ['empresa']

    def estat_colored(self, obj):
        colors = {
            'AC': 'green',
            'RV': 'orange',
            'OC': 'gray',
            'TC': 'red',
        }
        color = colors.get(obj.estat, 'black')
        label = obj.get_estat_display()
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>', color, label
        )
    
    estat_colored.short_description = "Estat"
    estat_colored.admin_order_field = 'estat'  # permet ordenar per estat real
    
    
    def descripcio_curta(self, obj):
        if not obj.descripcio:
            return "-"
        return obj.descripcio[:80] + "..." if len(obj.descripcio) > 80 else obj.descripcio

    descripcio_curta.short_description = "Descripció"


    def nombre_candidatures(self, obj):
        """Mostra el nombre total de candidatures"""
        return obj.candidatures.count()
    
    nombre_candidatures.short_description = "Candidatures"

    def get_urls(self):
        """
        Afegeix la nostra URL personalitzada per a l'acció del botó.
        Això es manté igual que a la solució anterior.
        """
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:oferta_id>/enviar-notificacio/',
                self.admin_site.admin_view(self.enviar_notificacio_view),
                name='enviar_notificacio_oferta',
            ),
        ]
        return custom_urls + urls

    def enviar_notificacio_view(self, request, oferta_id):
            """
            Aquesta vista s'executa quan es clica el botó.
            """
            # Engeguem la tasca de Huey
            # enviar_notificacio_nova_oferta(oferta_id)
            # enviar_email_async("prova","prova", ['rcerver4@xtec.cat'])
            #enviar_notificacio_nova_oferta(oferta_id)

            try:
                oferta = Oferta.objects.get(id=oferta_id)
            except Oferta.DoesNotExist:
                self.message_user(request, f"L'oferta {oferta_id} no existeix.", messages.ERROR)
                url = reverse('admin:borsa_treball_oferta_change', args=[oferta_id])
                return HttpResponseRedirect(url)
            
             # Obtenim els emails dels estudiants que han de ser notificats
            cicles_oferta_ids = oferta.cicles.values_list('id', flat=True)
            estudiants_a_notificar = Estudiant.objects.filter(estudis__cicle_id__in=cicles_oferta_ids).select_related('usuari').distinct()

            destinatari_list = [estudiant.usuari.email for estudiant in estudiants_a_notificar]
            if not destinatari_list:
                self.message_user(request, "No hi ha estudiants a notificar.", messages.WARNING)
            else:
                # Renderitzem la plantilla HTML un cop
                # Generar URL absoluta del login
                url_login = f"{settings.SITE_URL}{reverse('login')}"
                context = {'oferta': oferta, 'url_login': url_login}
                html_missatge = render_to_string('borsa_treball/emails/oferta_activada.html', context)
                missatge_text_pla = strip_tags(html_missatge)
                # Afegim un missatge de confirmació
                # self.message_user(request,   f"La tasca d'enviament s'ha engegat correctament per a {len(destinatari_list)} estudiants.",messages.SUCCESS)
                self.message_user(
                        request,
                        f"La tasca d'enviament de notificacions s'ha engegat correctament per a l'oferta actual.",
                        f"Correus enviats a: {', '.join(destinatari_list)}",                        
                        messages.SUCCESS
                    )
            # IMPORTANT: Redirigim de nou a la mateixa pàgina d'edició de l'oferta
            url = reverse('admin:borsa_treball_oferta_change', args=[oferta_id])
            return HttpResponseRedirect(url)

    def enviar_notificacio_view(self, request, oferta_id):
        """
        Aquesta vista s'executa quan es clica el botó al panell d'administració.
        """
        try:
            oferta = Oferta.objects.get(id=oferta_id)
        except Oferta.DoesNotExist:
            self.message_user(request, f"L'oferta {oferta_id} no existeix.", messages.ERROR)
            url = reverse('admin:borsa_treball_oferta_change', args=[oferta_id])
            return HttpResponseRedirect(url)

        cicles_oferta_ids = oferta.cicles.values_list('id', flat=True)
        estudiants_a_notificar = (
            Estudiant.objects
            .filter(estudis__cicle_id__in=cicles_oferta_ids)
            .select_related('usuari')
            .distinct()
        )

        estudiants_a_notificar = [e for e in estudiants_a_notificar if e.usuari.email]

        if not estudiants_a_notificar:
            self.message_user(request, "No hi ha estudiants a notificar.", messages.WARNING)
        else:
            url_login = f"{settings.SITE_URL}{reverse('login')}"

            for estudiant in estudiants_a_notificar:
                context = {
                    'oferta': oferta,
                    'url_login': url_login,
                    'nom_estudiant': estudiant.usuari.nom 
                }

                html_missatge = render_to_string('borsa_treball/emails/oferta_activada.html', context)
                missatge_text_pla = strip_tags(html_missatge)
                                
                enviar_email_async.schedule(
                    args=(
                        f"Nova oferta publicada: {oferta.titol}",
                        missatge_text_pla,
                        ['rcerver4@xtec.cat'],
                        html_missatge
                    ),
                    delay=2
                )

                
            self.message_user(
                    request,
                    f"S'han engegat les tasques d'enviament per a {len(estudiants_a_notificar)} estudiants.\n"
                    f"Destinataris: {', '.join(e.usuari.nom for e in estudiants_a_notificar)}",
                    messages.SUCCESS
                )

        url = reverse('admin:borsa_treball_oferta_change', args=[oferta_id])
        return HttpResponseRedirect(url)


from django.contrib import admin
from .models import Candidatura

class CandidaturaAdmin(admin.ModelAdmin):
    list_display = (
            'oferta_titol',
            'empresa_nom',
            'estudiant_nom',
            'data_candidatura',
            'estat',
            'activa',
            'cv_disponible',
    )
    list_filter = ('estat', 'activa', 'oferta__empresa__nom_comercial') 
   
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


    readonly_fields = (
        'data_candidatura', 
        'data_canvi_estat', 
        'descarregar_cv_admin',  # Nou camp
       
    )
    
    fieldsets = (
        ('Informació Bàsica', {
            'fields': ('oferta', 'estudiant', 'data_candidatura', 'estat', 'activa')
        }),
        ('Documents', {
            'fields': (
                'cv_adjunt', 
                'descarregar_cv_admin',  # Enllaç protegit
                'altres_adjunts', 
                
            )
        }),
        ('Detalls', {
            'fields': ('carta_presentacio', 'notes_empresa', 'puntuacio', 'data_canvi_estat')
        })
    )

    def oferta_titol(self, obj):
        return obj.oferta.titol
    oferta_titol.short_description = "Títol oferta"
    oferta_titol.admin_order_field = 'oferta__titol'


    def cv_disponible(self, obj):
        """Indica si hi ha CV a la llista"""
        if obj.cv_adjunt:
            cv_url = reverse('descarregar_cv_candidatura_admin', args=[obj.id])
            return format_html(
                '<a href="{}" target="_blank" style="color: green;">📄 Descarregar</a>',
                cv_url
            )
        return format_html('<span style="color: red;">❌ Sense CV</span>')
    cv_disponible.short_description = "CV"


    def descarregar_cv_admin(self, obj):
        """Versió més simple sense formatatge complex"""
        if not obj or not obj.pk:
            return "Desa primer la candidatura"
        
        if not obj.cv_adjunt:
            return "No hi ha CV adjunt"
        
        try:
            cv_url = reverse('descarregar_cv_candidatura_admin', args=[obj.id])
            mida_kb = round(obj.cv_adjunt.size / 1024, 1) if obj.cv_adjunt.size else 0
            
            return format_html(
                '<a href="{}" target="_blank" class="button default">📄 Descarregar CV</a><br>'
                '<small style="color: #666;">Mida: {} KB</small>',
                cv_url,
                mida_kb
            )
        except Exception as e:
            return format_html('Error: {}', str(e))

    descarregar_cv_admin.short_description = "CV"

    def empresa_nom(self, obj):
        return obj.oferta.empresa.nom_comercial
    empresa_nom.short_description = "Empresa"
    empresa_nom.admin_order_field = 'oferta__empresa__nom_comercial'

    def estudiant_nom(self, obj):
        return obj.estudiant.usuari.get_full_name()
    estudiant_nom.short_description = "Estudiant"
    estudiant_nom.admin_order_field = 'estudiant__usuari__nom'

class CandidaturaInline(admin.TabularInline):
    model = Candidatura
    extra = 0  # No mostrar files buides per defecte
    readonly_fields = ('data_candidatura', 'data_canvi_estat', 'temps_des_candidatura_display','cv_link_inline')
    fields = (
        'estudiant', 
        'estat', 
        'data_candidatura', 
        'data_canvi_estat',
        'puntuacio',
        'cv_link_inline', 
        'activa',
        'temps_des_candidatura_display'
    )
    
    def cv_link_inline(self, obj):
        """Enllaç curt per l'inline"""
        if obj.pk and obj.cv_adjunt:  # Només si l'objecte ja existeix
            cv_url = reverse('descarregar_cv_candidatura', args=[obj.id])
            return format_html(
                '<a href="{}" target="_blank" title="Descarregar CV">📄</a>',
                cv_url
            )
        return "-"
    cv_link_inline.short_description = "CV"

    
    def temps_des_candidatura_display(self, obj):
        """Mostra el temps transcorregut de forma llegible"""
        if obj.pk:  # Només si l'objecte ja existeix
            temps = obj.temps_des_candidatura
            dies = temps.days
            hores = temps.seconds // 3600
            
            if dies > 0:
                return f"{dies} dies, {hores} hores"
            elif hores > 0:
                return f"{hores} hores"
            else:
                return "Menys d'1 hora"
        return "-"
    
    temps_des_candidatura_display.short_description = "Temps des de candidatura"


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



from .models import OfertaExterna

@admin.register(OfertaExterna)
class OfertaExternaAdmin(admin.ModelAdmin):
    list_display = ('titol', 'entitat', 'data_limit', 'activa', 'data_publicacio')
    list_filter = ('activa', 'data_limit', 'entitat')
    search_fields = ('titol', 'descripcio', 'entitat')
    ordering = ('-data_publicacio',)
    date_hierarchy = 'data_publicacio'


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