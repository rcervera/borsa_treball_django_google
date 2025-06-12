
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
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        messages.error(request, 'No tens permisos per accedir a aquesta pàgina.')
        return redirect('index')

    oferta = get_object_or_404(Oferta, id=oferta_id, empresa=empresa)

    familias = FamiliaProfessional.objects.order_by('nom').prefetch_related(
        Prefetch(
            'cicle_set',  # El 'related_name' per defecte si no l'has definit explícitament a ForeignKey
            queryset=Cicle.objects.order_by('nom'),
            to_attr='cicles_de_la_familia' # Nom de l'atribut que contindrà els cicles per a cada família
        )
    )
    
    cicles_seleccionats_ids = set(oferta.cicles.values_list('id', flat=True))

    cicles_agrupats_per_familia = []
    for familia in familias:
        if hasattr(familia, 'cicles_de_la_familia'):
            # Filtrar només cicles **no seleccionats**
            cicles_data = [
                {
                    'id': cicle.id,
                    'nom': cicle.nom,
                    'grau': cicle.grau,
                    'familia_nom': familia.nom,
                    'familia_id': familia.id,
                }
                for cicle in familia.cicles_de_la_familia
                if cicle.id not in cicles_seleccionats_ids
            ]
            if cicles_data:  # Només incloure famílies amb cicles disponibles
                cicles_agrupats_per_familia.append({
                    'familia_nom': familia.nom,
                    'cicles': cicles_data
                })
  

    # Convertir dades relacionades en formats simples per injectar al JS
    funcions = list(oferta.funcions.values_list('descripcio', flat=True))
    # capacitats = list(oferta.capacitats_clau.values('id', 'nom', 'categoria'))
    cicles = list(oferta.cicles.values('id', 'nom', 'grau', 'familia__nom'))
    idiomes = list(oferta.idiomes.values('idioma', 'nivell'))

    capacitats = CapacitatClau.objects.all()

    capacitats_existents = list(oferta.capacitats_clau.values('id', 'nom', 'categoria'))
    capacitats_existents_ids = set(capacitat['id'] for capacitat in capacitats_existents)

    capacitats_disponibles = [
        capacitat for capacitat in capacitats
        if capacitat.id not in capacitats_existents_ids
    ]

    context = {
        'oferta': oferta,
        'cicles': Cicle.objects.all(),
        'cicles_agrupats_per_familia': cicles_agrupats_per_familia,
        'capacitats': capacitats_disponibles,
        'tipus_contracte_choices': Oferta.TIPUS_CONTRACTE,
        'jornada_choices': Oferta.JORNADA,
        'PUBLIC_DESTINATARI': Oferta.PUBLIC_DESTINATARI,
        'EXPERIENCIA': Oferta.EXPERIENCIA,
        'data_limit_formatted': oferta.data_limit.strftime('%Y-%m-%d') if oferta.data_limit else '',
        'funcions_existents': funcions,
        'capacitats_existents':  capacitats_existents,
        'cicles_existents': [
            {
                'id': c['id'],
                'nom': c['nom'],
                'grau': c['grau'],
                'familia': c['familia__nom']
            } for c in cicles
        ],
        'idiomes_existents': idiomes,
        'TIPUS_CONTRACTE': Oferta.TIPUS_CONTRACTE,
        'JORNADA': Oferta.JORNADA,
    }

    return render(request, 'borsa_treball/editar_oferta_empresa.html', context)

# EDIT API

@csrf_exempt
@require_http_methods(["PUT"])
@login_required
def api_actualitzar_oferta(request, oferta_id):
    try:
        empresa = request.user.empresa
    except:
        return JsonResponse({'success': False, 'message': 'No tens empresa associada'}, status=403)

    try:
        oferta = Oferta.objects.get(id=oferta_id, empresa=empresa)
    except Oferta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Oferta no trobada'}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Dades JSON no vàlides'}, status=400)

    # Assignació bàsica de camps
    oferta.titol = data.get("titol", "")
    oferta.data_limit = data.get("data_limit") or None
    oferta.numero_vacants = data.get("numero_vacants", 1)
    oferta.descripcio = data.get("descripcio", "")
    oferta.tipus_contracte = data.get("tipus_contracte", "")
    oferta.jornada = data.get("jornada", "")
    oferta.hores = data.get("hores") or None
    oferta.horari = data.get("horari", "")
    oferta.salari = data.get("salari", "")
    oferta.lloc_treball = data.get("lloc_treball", "")
    oferta.destinatari = data.get("destinatari", "")
    oferta.experiencia = data.get("experiencia", "")
    oferta.visible = data.get("visible", False)

    oferta.save()

   
    # Eliminar funcions antigues
    oferta.funcions.all().delete()
    # Afegir funcions noves
    for descripcio in data.get("funcions", []):
        Funcio.objects.create(oferta=oferta, descripcio=descripcio)


    oferta.cicles.set(data.get("cicles", []))
    oferta.capacitats_clau.set(data.get("capacitats_clau", []))

    oferta.idiomes.all().delete()
    for idioma in data.get("idiomes", []):
        oferta.idiomes.create(idioma=idioma.get("idioma", ""), nivell=idioma.get("nivell", ""))


    return JsonResponse({'success': True, 'message': 'Oferta actualitzada correctament'})


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
@login_required
def editar_perfil_empresa(request):
    """
    Vista per editar el perfil de l'empresa i l'usuari associat.
    Aquesta vista només renderitza el template amb les dades inicials.
    Els enviaments dels formularis es gestionaran per les vistes API.
    """
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        messages.error(request, 'No tens permisos per accedir a aquesta pàgina.')
        return redirect('index') # O la teva pàgina d'inici de sessió si és més apropiat
    
    context = {
        'empresa': empresa,
        'user': request.user,
        'sectors': Sector.objects.all().order_by('nom'),
    }
    return render(request, 'borsa_treball/editar_perfil_empresa.html', context)


@require_POST
@login_required
def api_canviar_contrasenya(request):
    """
    Vista API per canviar la contrasenya de l'usuari.
    Retorna JsonResponse amb 'success' i 'message' o 'errors'.
    """
    # El PasswordChangeForm necessita l'usuari actual i les dades del POST.
    form = PasswordChangeForm(user=request.user, data=request.POST)

    if form.is_valid():
        user = form.save()
        # Important: actualitza el hash de sessió per evitar que l'usuari es desconnecti
        update_session_auth_hash(request, user)
        return JsonResponse({'success': True, 'message': "Contrasenya canviada correctament."})
    else:
        # Si el formulari no és vàlid, capturem els errors per camp.
        # form.errors és un diccionari amb els errors.
        # Per exemple: {'old_password': ['Contrasenya incorrecta.'], 'new_password1': ['Aquesta contrasenya és massa curta.']}
        
        # Convertim els errors del formulari a un format que el JS pugui processar fàcilment.
        # El diccionari form.errors ja fa la feina, només cal assegurar-se que els valors són llistes de strings.
        
        # PasswordChangeForm té els camps: old_password, new_password1, new_password2
        # Els errors per camp seran accessibles directament.
        
        # Si vols ser més explícit i retornar només els camps que et surten a la plantilla:
        specific_errors = {}
        if 'old_password' in form.errors:
            specific_errors['old_password'] = form.errors['old_password']
        if 'new_password1' in form.errors:
            specific_errors['new_password1'] = form.errors['new_password1']
        if 'new_password2' in form.errors:
            specific_errors['new_password2'] = form.errors['new_password2']
        
        # En comptes de specific_errors, pots enviar directament form.errors si el teu JS pot manejar-ho.
        # Per simplicitat i compatibilitat amb el que ja tenies, specific_errors és més segur.
        return JsonResponse({'success': False, 'errors': specific_errors})



from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError
from django.core.validators import validate_email 
import re 
import json 

# Importa els teus models
from .models import Empresa, Usuari, Sector # Assegura't que Usuari i Sector estan correctament importats


# --- Vista original (renderitza el template) ---
@login_required
def editar_perfil_empresa(request):
    """
    Vista per editar el perfil de l'empresa i l'usuari associat.
    Aquesta vista només renderitza el template amb les dades inicials.
    Els enviaments dels formularis es gestionaran per les vistes API.
    """
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        messages.error(request, 'No tens permisos per accedir a aquesta pàgina.')
        return redirect('index') 
    
    context = {
        'empresa': empresa,
        'user': request.user,
        'sectors': Sector.objects.all().order_by('nom'),
    }
    return render(request, 'borsa_treball/editar_perfil_empresa.html', context)


# --- NOVA VISTA API per la informació de l'Empresa (Validació manual) ---
@require_POST
@login_required
def api_editar_perfil_empresa(request):
    """
    Vista API per actualitzar la informació del perfil de l'empresa.
    Realitza validacions manuals i retorna JsonResponse amb 'success' i 'message' o 'errors' per camp.
    """
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Empresa no trobada.'}, status=404)

    errors = {} # Diccionari per emmagatzemar errors per camp

    # Neteja i validació dels camps de l'Empresa, basats EXACTAMENT en el teu MODEL DEFINITIU
    nom_comercial = request.POST.get('nom_comercial', '').strip()
    if not nom_comercial:
        errors.setdefault('nom_comercial', []).append('El nom comercial és obligatori.')
    
    rao_social = request.POST.get('rao_social', '').strip()
    if not rao_social:
        errors.setdefault('rao_social', []).append('La raó social és obligatòria.')

    cif = request.POST.get('cif', '').strip().upper()
    if not cif:
        errors.setdefault('cif', []).append('El CIF és obligatori.')
    else:
        # Validació de format de CIF: 9 caràcters alfanumèrics (el teu model té max_length=9)
        cif_pattern = r'^[0-9A-Z]{9}$' # Permet números i lletres, 9 caràcters
        if not re.match(cif_pattern, cif):
            errors.setdefault('cif', []).append('El CIF ha de tenir 9 caràcters (lletres o números).')
        # Validació d'unicitat del CIF
        if Empresa.objects.filter(cif=cif).exclude(usuari=request.user).exists():
            errors.setdefault('cif', []).append('Aquest CIF ja està registrat per una altra empresa.')

    telefon = request.POST.get('telefon', '').strip()
    # Telefon no és obligatori segons el teu model (blank=True, null=True, max_length=15)
    if telefon and not re.match(r'^\+?[0-9\s\-\(\)]{1,15}$', telefon):
        errors.setdefault('telefon', []).append('El telèfon no té un format vàlid (pot incloure "+" al principi, números, espais, guions i parèntesis; màxim 15 caràcters).')

    email_contacte = request.POST.get('email_contacte', '').strip()
    # Email de contacte no és obligatori segons el teu model (blank=True, null=True)
    if email_contacte:
        try:
            validate_email(email_contacte)
        except ValidationError:
            errors.setdefault('email_contacte', []).append('L\'email de contacte no té un format vàlid.')

    num_treballadors_str = request.POST.get('num_treballadors', '').strip()
    num_treballadors = None 
    # num_treballadors no és obligatori segons el teu model (blank=True, null=True)
    if num_treballadors_str:
        try:
            num_treballadors = int(num_treballadors_str)
            if num_treballadors < 0:
                errors.setdefault('num_treballadors', []).append('El número de treballadors ha de ser positiu.')
        except ValueError:
            errors.setdefault('num_treballadors', []).append('El número de treballadors ha de ser un nombre enter.')

    sector_id = request.POST.get('sector', '')
    sector_obj = None
    # Sector no és obligatori segons el teu model (null=True)
    if sector_id:
        try:
            sector_obj = Sector.objects.get(id=sector_id)
        except Sector.DoesNotExist:
            errors.setdefault('sector', []).append('El sector seleccionat no és vàlid.')
    
    web = request.POST.get('web', '').strip()
    # Web no és obligatori segons el teu model (blank=True, null=True)
    if web and not web.startswith(('http://', 'https://')):
        web = 'https://' + web
    # Validació de format d'URL bàsica (més exhaustiva amb Django forms)
    if web and not re.match(r'^https?://[^\s/$.?#].[^\s]*$', web):
        errors.setdefault('web', []).append('La pàgina web no té un format vàlid.')
    
    descripcio = request.POST.get('descripcio', '').strip()
    # Descripcio no és obligatori segons el teu model (blank=True, null=True)


    if errors:
        return JsonResponse({'success': False, 'errors': json.dumps(errors)})
    
    try:
        # Si no hi ha errors, actualitzem els camps de l'empresa
        empresa.nom_comercial = nom_comercial
        empresa.rao_social = rao_social
        empresa.cif = cif
        empresa.telefon = telefon if telefon else None 
        empresa.email_contacte = email_contacte if email_contacte else None
        empresa.num_treballadors = num_treballadors
        empresa.sector = sector_obj
        empresa.web = web if web else None
        empresa.descripcio = descripcio if descripcio else None
        
        empresa.save()
        return JsonResponse({'success': True, 'message': 'Informació de l\'empresa actualitzada correctament.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error en guardar la informació de l\'empresa: {str(e)}'}, status=500)


# --- NOVA VISTA API per la informació del Contacte (Usuari) (Validació manual) ---
@require_POST
@login_required
def api_editar_perfil_usuari(request):
    """
    Vista API per actualitzar la informació del contacte (usuari associat).
    Realitza validacions manuals i retorna JsonResponse amb 'success' i 'message' o 'errors' per camp.
    """
    user = request.user
    errors = {} # Diccionari per emmagatzemar errors per camp

    # Neteja i validació dels camps de l'Usuari
    nom = request.POST.get('nom', '').strip()
    if not nom:
        errors.setdefault('nom', []).append('El nom és obligatori.')
    
    cognoms = request.POST.get('cognoms', '').strip()
    if not cognoms:
        errors.setdefault('cognoms', []).append('Els cognoms són obligatoris.')
    
    # L'email de l'usuari es mostra deshabilitat al frontend, no es modifica des d'aquí.

    if errors:
        return JsonResponse({'success': False, 'errors': json.dumps(errors)})

    try:
        user.nom = nom
        user.cognoms = cognoms
        user.save()
        
        return JsonResponse({'success': True, 'message': 'Informació del contacte actualitzada correctament.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error en guardar la informació de contacte: {str(e)}'}, status=500)


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, logout # Importa logout
from django.core.exceptions import ValidationError 
from django.core.validators import validate_email 
import re 
import json 

@require_POST # Assegura que només s'acceptin peticions POST
@login_required
def eliminar_perfil_empresa(request):
    """
    Vista per eliminar el perfil d'empresa i l'usuari associat.
    Aquesta acció és irreversible.
    """
    try:
        # Obtenim l'objecte Usuari de la sessió actual
        user_to_delete = request.user 
        # Obtenim l'objecte Empresa associat a aquest usuari (si existeix)
        # No cal comprovar Empresa.DoesNotExist aquí, ja que eliminar Usuari
        # hauria de fer cascada l'eliminació d'Empresa si el OneToOneField és correcte.
        # Si hi ha AttributeError, vol dir que no és un usuari amb empresa.
        empresa_associada = user_to_delete.empresa 
    except (Empresa.DoesNotExist, AttributeError):
        # Si no hi ha empresa associada o l'usuari no és de tipus empresa
        messages.error(request, 'No s\'ha trobat un perfil d\'empresa vàlid associat al teu usuari.')
        return redirect('index') # O una altra pàgina adequada (ex: home de l'app)

    try:
        # PRIMER: Tancar la sessió de l'usuari. És crucial fer-ho abans d'eliminar el compte.
        logout(request) 

        # Ara, eliminem l'objecte Usuari.
        # Com que el camp `usuari` al model `Empresa` té `on_delete=models.CASCADE`
        # i `primary_key=True`, en eliminar l'usuari, l'empresa vinculada també s'eliminarà AUTOMÀTICAMENT.
        user_to_delete.delete() 
        
        messages.success(request, 'El teu perfil d\'empresa i el compte d\'usuari han estat eliminats correctament.')
        return redirect('login') # Redirigir a la pàgina d'inici de sessió o una pàgina de confirmació.
    except Exception as e:
        messages.error(request, f'Hi ha hagut un error en eliminar el perfil: {str(e)}. Si el problema persisteix, contacta amb suport.')
        # Després d'un logout, ja no estem autenticats. Redirigir a login és el més segur.
        return redirect('login') 
