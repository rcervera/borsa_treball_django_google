
from django.forms import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Oferta, Empresa, Cicle, CapacitatClau,Funcio, Sector, Usuari, NivellIdioma, FamiliaProfessional

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.core.validators import validate_email
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_POST
from django.db.models import Prefetch


#
# AFEGIR OFERTA
#



@login_required
def afegir_oferta_directe(request):

    # Recuperar totes les famílies professionals i precarregar els seus cicles associats
    # Utilitzem Prefetch per carregar els cicles de cada família de manera eficient
    # i els ordenem per nom, tant les famílies com els cicles dins de cada família.
    familias = FamiliaProfessional.objects.order_by('nom').prefetch_related(
        Prefetch(
            'cicle_set',  # El 'related_name' per defecte si no l'has definit explícitament a ForeignKey
            queryset=Cicle.objects.order_by('nom'),
            to_attr='cicles_de_la_familia' # Nom de l'atribut que contindrà els cicles per a cada família
        )
    )
    
    cicles_agrupats_per_familia = []
    for familia in familias:
        # Si la família té cicles, els afegim a la llista agrupada
        if hasattr(familia, 'cicles_de_la_familia') and familia.cicles_de_la_familia:
            cicles_data = [
                {
                    'id': cicle.id, 
                    'nom': cicle.nom, 
                    'grau': cicle.grau,
                    'familia_nom': familia.nom, # Afegim el nom de la família per a l'atribut data-familia
                    'familia_id': familia.id # Si en algun moment necessites l'ID de la família
                }
                for cicle in familia.cicles_de_la_familia
            ]
            cicles_agrupats_per_familia.append({
                'familia_nom': familia.nom,
                'cicles': cicles_data
            })
  
   # AFEGEIX AQUEST PRINT:
    print("\n--- Contingut de cicles_agrupats_per_familia ---")
    import json
    print(json.dumps(cicles_agrupats_per_familia, indent=2, ensure_ascii=False))
    print("--------------------------------------------------\n")

    # GET -> mostrar formulari
    context = {
    'cicles': Cicle.objects.all(),
    'cicles_agrupats_per_familia': cicles_agrupats_per_familia,
    'capacitats': CapacitatClau.objects.all(),
    'TIPUS_CONTRACTE': Oferta.TIPUS_CONTRACTE,
    'JORNADA': Oferta.JORNADA,
    'PUBLIC_DESTINATARI': Oferta.PUBLIC_DESTINATARI,
    'EXPERIENCIA': Oferta.EXPERIENCIA,
    }
    return render(request, 'borsa_treball/afegir_oferta_empresa.html', context)

#
# AFEGIR OFERTA API
#
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
import json

@csrf_exempt
@require_POST
def crear_oferta_api(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'errors': {'global': 'Dades JSON no vàlides'}}, status=400)

    errors = {}

    titol = data.get('titol', '').strip()
    if not titol:
        errors['titol'] = "El títol és obligatori."

    data_limit = data.get('data_limit')
    if not data_limit:
        errors['data_limit'] = "La data límit és obligatòria."

    descripcio = data.get('descripcio', '').strip()
    if not descripcio:
        errors['descripcio'] = "La descripció és obligatòria."

    tipus_contracte = data.get('tipus_contracte')
    if not tipus_contracte:
        errors['tipus_contracte'] = "Tipus de contracte obligatori."

    jornada = data.get('jornada')
    if not jornada:
        errors['jornada'] = "Jornada obligatòria."

    lloc_treball = data.get('lloc_treball', '').strip()
    if not lloc_treball:
        errors['lloc_treball'] = "Lloc de treball obligatori."

    destinatari = data.get('destinatari', 'AMB')
    experiencia = data.get('experiencia')

    # Validació numero_vacants
    numero_vacants = data.get('numero_vacants')
    vacants_valor = None
    if numero_vacants is None or str(numero_vacants).strip() == '':
        errors['numero_vacants'] = "Cal indicar el nombre de vacants."
    else:
        try:
            vacants_valor = int(numero_vacants)
            if vacants_valor <= 0:
                errors['numero_vacants'] = "El nombre de vacants ha de ser positiu."
        except ValueError:
            errors['numero_vacants'] = "El valor ha de ser un número enter."

    # Validació hores si jornada parcial
    hores = data.get('hores')
    hores_valor = None
    if jornada == 'PA':
        if hores is None or str(hores).strip() == '':
            errors['hores'] = "Has d'indicar el nombre d'hores si la jornada és parcial."
        else:
            try:
                hores_valor = int(hores)
                if hores_valor <= 0:
                    errors['hores'] = "El nombre d'hores ha de ser positiu."
            except ValueError:
                errors['hores'] = "El valor d'hores ha de ser un número enter."

    cicles_ids = data.get('cicles', [])
    if not cicles_ids:
        errors['cicles'] = "Has de seleccionar almenys un cicle."

    if errors:
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    empresa = Empresa.objects.filter(usuari=request.user).first()
    if not empresa:
        return JsonResponse({'success': False, 'errors': {'global': 'Usuari no vàlid o no és una empresa'}}, status=403)

    oferta = Oferta.objects.create(
        empresa=empresa,
        titol=titol,
        descripcio=descripcio,
        data_limit=parse_date(data_limit),
        tipus_contracte=tipus_contracte,
        jornada=jornada,
        hores_setmanals=hores_valor,
        horari=data.get('horari', ''),
        salari=data.get('salari', ''),
        requisits='',
        lloc_treball=lloc_treball,
        contacte_nom=empresa.nom_comercial,
        contacte_email=request.user.email,
        contacte_telefon=empresa.telefon or '',
        public_destinatari=destinatari,
        experiencia=experiencia,
        visible=data.get('visible', True),
    )

    # Relacions many-to-many
    oferta.cicles.set(Cicle.objects.filter(id__in=cicles_ids))

    capacitats_ids = data.get('capacitats_clau', [])
    if capacitats_ids:
        oferta.capacitats_clau.set(CapacitatClau.objects.filter(id__in=capacitats_ids))

    for ordre, desc in enumerate(data.get('funcions', []), start=1):
        if desc.strip():
            Funcio.objects.create(oferta=oferta, descripcio=desc.strip(), ordre=ordre)

    for idioma in data.get('idiomes', []):
        nom = idioma.get('nom', '').strip()
        nivell = idioma.get('nivell', '').strip()
        if nom and nivell:
            NivellIdioma.objects.create(oferta=oferta, idioma=nom, nivell=nivell)

    return JsonResponse({'success': True, 'message': 'Oferta creada correctament'})

#
# LLISTA OFERTES
#

@login_required
def llista_ofertes(request):
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        return redirect('index')
    
    # Obtenir totes les ofertes de l'empresa
    ofertes = empresa.ofertes.all()
    
    # Filtres
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    jornada_filter = request.GET.get('jornada', '')
    order_by = request.GET.get('order_by', '-data_publicacio')
    
    # Aplicar filtres de cerca
    if search_query:
        ofertes = ofertes.filter(
            Q(titol__icontains=search_query) |
            Q(descripcio__icontains=search_query) |
            Q(lloc_treball__icontains=search_query)
        )
    
    # Filtrar per estat
    if status_filter:
        today = timezone.now().date()
        if status_filter == 'activa':
            # Ofertes visibles i no caducades
            ofertes = ofertes.filter(data_limit__gte=today, visible=True)
        elif status_filter == 'caducada':
            # Ofertes caducades
            ofertes = ofertes.filter(data_limit__lt=today)
        elif status_filter == 'oculta':
            # Ofertes ocultes (no visibles)
            ofertes = ofertes.filter(visible=False)
        elif status_filter == 'totes':
            pass  # No filtrar
    
    # Filtrar per tipus de contracte
    if type_filter:
        ofertes = ofertes.filter(tipus_contracte=type_filter)
    
    # Filtrar per jornada
    if jornada_filter:
        ofertes = ofertes.filter(jornada=jornada_filter)
    
    # Ordenació
    valid_order_fields = [
        'data_publicacio', '-data_publicacio',
        'data_limit', '-data_limit',
        'titol', '-titol',
        'candidatures_count', '-candidatures_count'
    ]
    
    if order_by in valid_order_fields:
        if 'candidatures_count' in order_by:
            # Anotar amb el count de candidatures per ordenar
            ofertes = ofertes.annotate(
                candidatures_count=Count('candidatures')
            ).order_by(order_by)
        else:
            ofertes = ofertes.order_by(order_by)
    else:
        ofertes = ofertes.order_by('-data_publicacio')
    
    # Estadístiques generals
    today = timezone.now().date()
    stats = {
        'total': empresa.ofertes.count(),
        'actives': empresa.ofertes.filter(data_limit__gte=today, visible=True).count(),
        'caducades': empresa.ofertes.filter(data_limit__lt=today).count(),
        'ocultes': empresa.ofertes.filter(visible=False).count(),
    }
    
    # Paginació
    items_per_page = request.GET.get('per_page', 6)
    try:
        items_per_page = int(items_per_page)
        if items_per_page not in [6, 12, 24]:
            items_per_page = 6
    except (ValueError, TypeError):
        items_per_page = 6
    
    paginator = Paginator(ofertes, items_per_page)
    page = request.GET.get('page', 1)
    
    try:
        ofertes_page = paginator.page(page)
    except PageNotAnInteger:
        ofertes_page = paginator.page(1)
    except EmptyPage:
        ofertes_page = paginator.page(paginator.num_pages)
    
    # Opcions per als filtres (usant els choices del model)
    tipus_contracte_choices = Oferta.TIPUS_CONTRACTE
    jornada_choices = Oferta.JORNADA
    
    status_choices = [
        ('', 'Tots els estats'),
        ('activa', 'Actives'),
        ('caducada', 'Caducades'),
        ('oculta', 'Ocultes'),
    ]
    
    order_choices = [
        ('-data_publicacio', 'Més recents'),
        ('data_publicacio', 'Més antigues'),
        ('-data_limit', 'Data límit (desc)'),
        ('data_limit', 'Data límit (asc)'),
        ('titol', 'Títol (A-Z)'),
        ('-titol', 'Títol (Z-A)'),
        ('-candidatures_count', 'Més candidatures'),
        ('candidatures_count', 'Menys candidatures'),
    ]
    
    context = {
        'ofertes': ofertes_page,
        'stats': stats,
        'search_query': search_query,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'jornada_filter': jornada_filter,
        'order_by': order_by,
        'items_per_page': items_per_page,
        'tipus_contracte_choices': tipus_contracte_choices,
        'jornada_choices': jornada_choices,
        'status_choices': status_choices,
        'order_choices': order_choices,
        'total_results': paginator.count,
    }
    
    return render(request, 'borsa_treball/llista_ofertes_empresa.html', context)

#
#  AMAGAR/MOSTRAR OFERTS: API 
#

@login_required
@require_http_methods(["POST"])
def toggle_visibilitat_oferta(request, oferta_id):
    """
    Vista per canviar la visibilitat d'una oferta (visible/oculta).
    """
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'No tens permisos per realitzar aquesta acció.'
        }, status=403)
    
    oferta = get_object_or_404(Oferta, id=oferta_id, empresa=empresa)
    
    try:
        # Canviar la visibilitat
        oferta.visible = not oferta.visible
        oferta.save()
        
        status_text = "visible" if oferta.visible else "oculta"
        
        return JsonResponse({
            'success': True,
            'message': f'L\'oferta "{oferta.titol}" ara és {status_text}.',
            'visible': oferta.visible,
            'oferta_id': oferta.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error en canviar la visibilitat: {str(e)}'
        }, status=500)

#
#   ELIMINAR OFERTA
#     

@login_required
@require_http_methods(["POST", "DELETE"])
def esborrar_oferta(request, oferta_id):
    """
    Vista per esborrar una oferta.
    Només permet esborrar ofertes de l'empresa de l'usuari autenticat.
    """
    try:
        # Verificar que l'usuari té una empresa associada
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'No tens permisos per realitzar aquesta acció.'
        }, status=403)
    
    # Obtenir l'oferta i verificar que pertany a l'empresa de l'usuari
    oferta = get_object_or_404(Oferta, id=oferta_id, empresa=empresa)
    
    try:
        # Guardar informació de l'oferta abans d'esborrar-la
        oferta_info = {
            'id': oferta.id,
            'titol': oferta.titol,
            'empresa': oferta.empresa.nom_comercial
        }
        
        # Esborrar l'oferta
        oferta.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'L\'oferta "{oferta_info["titol"]}" s\'ha eliminat correctament.',
            'oferta_id': oferta_info['id']
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error en eliminar l\'oferta: {str(e)}'
        }, status=500)
    

#
# DETALL OFERTA
#

@login_required
def detall_oferta(request, oferta_id):
    """
    Vista per veure els detalls complets d'una oferta.
    """
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        messages.error(request, 'No tens permisos per accedir a aquesta pàgina.')
        return redirect('index')
    
    # Obtenir l'oferta i verificar que pertany a l'empresa
    oferta = get_object_or_404(Oferta, id=oferta_id, empresa=empresa)
    
    # Calcular estadístiques
    today = timezone.now().date()
    dies_restants = (oferta.data_limit - today).days if oferta.data_limit > today else 0
    
    # Estat de l'oferta
    if not oferta.visible:
        estat = 'oculta'
        estat_class = 'secondary'
        estat_icon = 'eye-slash'
    elif oferta.data_limit < today:
        estat = 'caducada'
        estat_class = 'danger'
        estat_icon = 'x-circle'
    else:
        estat = 'activa'
        estat_class = 'success'
        estat_icon = 'check-circle'
    
    context = {
        'oferta': oferta,
        'dies_restants': dies_restants,
        'estat': estat,
        'estat_class': estat_class,
        'estat_icon': estat_icon,
        'today': today,
    }
    
    return render(request, 'borsa_treball/detall_oferta_empresa.html', context)


#
# EDITAR EMPRESA
#
@login_required
def editar_oferta(request, oferta_id):
    """
    Vista per editar una oferta existent.
    """
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        messages.error(request, 'No tens permisos per accedir a aquesta pàgina.')
        return redirect('index')
    
    # Obtenir l'oferta i verificar que pertany a l'empresa
    oferta = get_object_or_404(Oferta, id=oferta_id, empresa=empresa)
    
    if request.method == 'POST':
        try:
            # Dades bàsiques
            oferta.titol = request.POST.get('titol', '').strip()
            oferta.descripcio = request.POST.get('descripcio', '').strip()
            oferta.lloc_treball = request.POST.get('lloc_treball', '').strip()
            oferta.tipus_contracte = request.POST.get('tipus_contracte', '')
            oferta.jornada = request.POST.get('jornada', '')
            oferta.horari = request.POST.get('horari', '').strip()
            oferta.salari = request.POST.get('salari', '').strip()
            oferta.requisits = request.POST.get('requisits', '').strip()
            
            # Data límit
            data_limit_str = request.POST.get('data_limit', '')
            if data_limit_str:
                oferta.data_limit = datetime.strptime(data_limit_str, '%Y-%m-%d').date()
            
            # Contacte
            oferta.contacte_nom = request.POST.get('contacte_nom', '').strip()
            oferta.contacte_email = request.POST.get('contacte_email', '').strip()
            oferta.contacte_telefon = request.POST.get('contacte_telefon', '').strip()
            
            # Visibilitat
            oferta.visible = request.POST.get('visible') == 'on'
            
            # Validacions bàsiques
            errors = []
            
            if not oferta.titol:
                errors.append('El títol és obligatori.')
            
            if not oferta.descripcio:
                errors.append('La descripció és obligatòria.')
            
            if not oferta.lloc_treball:
                errors.append('El lloc de treball és obligatori.')
            
            if not oferta.tipus_contracte:
                errors.append('El tipus de contracte és obligatori.')
            
            if not oferta.jornada:
                errors.append('La jornada és obligatòria.')
            
            if not oferta.data_limit:
                errors.append('La data límit és obligatòria.')
            elif oferta.data_limit <= timezone.now().date():
                errors.append('La data límit ha de ser posterior a avui.')
            
            if not oferta.contacte_nom:
                errors.append('El nom de contacte és obligatori.')
            
            if not oferta.contacte_email:
                errors.append('L\'email de contacte és obligatori.')
            
            if not oferta.contacte_telefon:
                errors.append('El telèfon de contacte és obligatori.')
            
            # Gestionar funcions
            funcions_list = request.POST.getlist('funcions')
            funcions_filtrades = [f.strip() for f in funcions_list if f.strip()]
            
            if not funcions_filtrades:
                errors.append('Has d\'afegir almenys una funció a l\'oferta.')
            
            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'core/editar_oferta.html', {
                    'oferta': oferta,
                    'cicles': Cicle.objects.all(),
                    'capacitats': CapacitatClau.objects.all(),
                    'tipus_contracte_choices': Oferta.TIPUS_CONTRACTE,
                    'jornada_choices': Oferta.JORNADA,
                    'data_limit_formatted': oferta.data_limit.strftime('%Y-%m-%d') if oferta.data_limit else '',
                    'funcions_existents': [f.descripcio for f in oferta.funcions.all()],
                })
            
            # Guardar l'oferta
            oferta.save()
            
            # Gestionar funcions - eliminar les existents i crear les noves
            oferta.funcions.all().delete()
            for i, funcio_desc in enumerate(funcions_filtrades, 1):
                Funcio.objects.create(
                    oferta=oferta,
                    descripcio=funcio_desc,
                    ordre=i
                )
            
            # Gestionar cicles (Many-to-Many)
            cicles_ids = request.POST.getlist('cicles')
            if cicles_ids:
                cicles = Cicle.objects.filter(id__in=cicles_ids)
                oferta.cicles.set(cicles)
            else:
                oferta.cicles.clear()
            
            # Gestionar capacitats clau (Many-to-Many)
            capacitats_ids = request.POST.getlist('capacitats_clau')
            if capacitats_ids:
                capacitats = CapacitatClau.objects.filter(id__in=capacitats_ids)
                oferta.capacitats_clau.set(capacitats)
            else:
                oferta.capacitats_clau.clear()
            
            messages.success(request, f'L\'oferta "{oferta.titol}" s\'ha actualitzat correctament.')
            return redirect('llista_ofertes')
            
        except ValueError as e:
            messages.error(request, f'Error en el format de les dades: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error en actualitzar l\'oferta: {str(e)}')
    
    # GET request - mostrar formulari amb dades precarregades
    context = {
        'oferta': oferta,
        'cicles': Cicle.objects.all(),
        'capacitats': CapacitatClau.objects.all(),
        'tipus_contracte_choices': Oferta.TIPUS_CONTRACTE,
        'jornada_choices': Oferta.JORNADA,
        'data_limit_formatted': oferta.data_limit.strftime('%Y-%m-%d') if oferta.data_limit else '',
        'funcions_existents': [f.descripcio for f in oferta.funcions.all()],
        'TIPUS_CONTRACTE': Oferta.TIPUS_CONTRACTE,
        'JORNADA': Oferta.JORNADA,
    }
    
    return render(request, 'borsa_treball/editar_oferta_empresa.html', context)

#
# DUPLICAR OFERTA
#
@login_required
def duplicar_oferta(request, oferta_id):
    """
    Vista per duplicar una oferta existent.
    """
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        messages.error(request, 'No tens permisos per accedir a aquesta pàgina.')
        return redirect('index')
    
    # Obtenir l'oferta original i verificar que pertany a l'empresa
    oferta_original = get_object_or_404(Oferta, id=oferta_id, empresa=empresa)
    
    try:
        # Crear la nova oferta amb les dades de l'original
        nova_oferta = Oferta.objects.create(
            empresa=empresa,
            titol=f"Còpia de {oferta_original.titol}",
            descripcio=oferta_original.descripcio,
            lloc_treball=oferta_original.lloc_treball,
            tipus_contracte=oferta_original.tipus_contracte,
            jornada=oferta_original.jornada,
            horari=oferta_original.horari,
            salari=oferta_original.salari,
            requisits=oferta_original.requisits,
            data_limit=timezone.now().date() + timedelta(days=30),  # 30 dies des d'avui
            contacte_nom=oferta_original.contacte_nom,
            contacte_email=oferta_original.contacte_email,
            contacte_telefon=oferta_original.contacte_telefon,
            visible=False  # Començar com a oculta perquè la revisin
        )
        
        # Copiar les relacions many-to-many
        # Cicles
        nova_oferta.cicles.set(oferta_original.cicles.all())
        
        # Capacitats clau
        nova_oferta.capacitats_clau.set(oferta_original.capacitats_clau.all())
        
        # Copiar les funcions
        for funcio_original in oferta_original.funcions.all():
            Funcio.objects.create(
                oferta=nova_oferta,
                descripcio=funcio_original.descripcio,
                ordre=funcio_original.ordre
            )
        
        messages.success(
            request, 
            f'S\'ha creat una còpia de l\'oferta "{oferta_original.titol}". '
            f'Revisa i modifica les dades necessàries abans de publicar-la.'
        )
        
        # Redirigir a l'edició de la nova oferta
        return redirect('editar_oferta', oferta_id=nova_oferta.id)
        
    except Exception as e:
        messages.error(request, f'Error en duplicar l\'oferta: {str(e)}')
        return redirect('detall_oferta', oferta_id=oferta_id)


#
# EDITAR PERFIL 
#


from django.contrib.auth import update_session_auth_hash
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re

@login_required
def editar_perfil_empresa(request):
    """
    Vista per editar el perfil de l'empresa i l'usuari associat.
    """
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        messages.error(request, 'No tens permisos per accedir a aquesta pàgina.')
        return redirect('index')
    
    if request.method == 'POST':
        try:
            user = request.user
            user.nom = request.POST.get('nom', '').strip()
            user.cognoms = request.POST.get('cognoms', '').strip()
            user.telefon = request.POST.get('telefon_usuari', '').strip()
            nou_email = request.POST.get('email', '').strip()

            empresa.nom_comercial = request.POST.get('nom_comercial', '').strip()
            empresa.rao_social = request.POST.get('rao_social', '').strip()
            empresa.cif = request.POST.get('cif', '').strip().upper()
            empresa.descripcio = request.POST.get('descripcio', '').strip()
            empresa.web = request.POST.get('web', '').strip()
            empresa.telefon = request.POST.get('telefon', '').strip()

            num_treballadors_str = request.POST.get('num_treballadors', '').strip()
            if num_treballadors_str:
                try:
                    empresa.num_treballadors = int(num_treballadors_str)
                except ValueError:
                    empresa.num_treballadors = None
            else:
                empresa.num_treballadors = None

            sector_id = request.POST.get('sector', '')
            if sector_id:
                try:
                    sector = Sector.objects.get(id=sector_id)
                    empresa.sector = sector
                except Sector.DoesNotExist:
                    empresa.sector = None
            else:
                empresa.sector = None

            errors = []

            # Validació de l'usuari
            if not user.nom:
                errors.append('El nom és obligatori.')
            if not user.cognoms:
                errors.append('Els cognoms són obligatoris.')
            if not nou_email:
                errors.append('L\'email és obligatori.')
            else:
                try:
                    validate_email(nou_email)
                    if Usuari.objects.filter(email=nou_email).exclude(id=user.id).exists():
                        errors.append('Aquest email ja està en ús per un altre usuari.')
                except ValidationError:
                    errors.append('L\'email no té un format vàlid.')

            # Validació empresa
            if not empresa.nom_comercial:
                errors.append('El nom comercial és obligatori.')
            if not empresa.rao_social:
                errors.append('La raó social és obligatòria.')
            if not empresa.telefon:
                errors.append('El telèfon és obligatori.')
            if not empresa.cif:
                errors.append('El CIF és obligatori.')
            else:
                cif_pattern = r'^[ABCDEFGHJNPQRSUVW]\d{8}$'
                if not re.match(cif_pattern, empresa.cif):
                    errors.append('El CIF no té un format vàlid (ex: A12345678).')
                if Empresa.objects.filter(cif=empresa.cif).exclude(usuari=user).exists():
                    errors.append('Aquest CIF ja està registrat per una altra empresa.')

            if empresa.num_treballadors is not None and empresa.num_treballadors < 0:
                errors.append('El número de treballadors ha de ser positiu.')
            if empresa.web and not empresa.web.startswith(('http://', 'https://')):
                empresa.web = 'https://' + empresa.web

            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'borsa_treball/editar_perfil_empresa.html', {
                    'empresa': empresa,
                    'user': user,
                    'sectors': Sector.objects.all().order_by('nom'),
                })

            # Actualitzar email només si és diferent
            if user.email != nou_email:
                user.email = nou_email

            user.save()
            empresa.save()

            # 🔒 Mantenim sessió activa en cas de canvi d'email (USERNAME_FIELD)
            update_session_auth_hash(request, user)

            messages.success(request, 'El perfil s\'ha actualitzat correctament.')
            return redirect('editar_perfil_empresa')

        except Exception as e:
            messages.error(request, f'Error en actualitzar el perfil: {str(e)}')

    context = {
        'empresa': empresa,
        'user': request.user,
        'sectors': Sector.objects.all().order_by('nom'),
    }
    return render(request, 'borsa_treball/editar_perfil_empresa.html', context)



@require_POST
@login_required
def api_canviar_contrasenya(request):
    form = PasswordChangeForm(user=request.user, data=request.POST)

    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)  # Evita que es tanqui la sessió
        return JsonResponse({'success': True, 'message': "Contrasenya canviada correctament."})

    # Si hi ha errors, retornem la llista
    errors = []
    for field_errors in form.errors.values():
        errors.extend(field_errors)

    return JsonResponse({'success': False, 'errors': errors})