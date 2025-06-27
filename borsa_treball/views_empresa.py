
# Imports estàndard de Python
import json
import mimetypes
import os
import re
from datetime import datetime, timedelta

# Imports de Django - Core
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, logout
from django.contrib.auth.decorators import login_required

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q, Count, Prefetch
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

# Imports locals
from .models import (
    Candidatura,
    CapacitatOferta, 
    EstatCandidatura, 
    Oferta, 
    Empresa, 
    Cicle, 
    CapacitatClau,
    Funcio, 
    Sector, 
    Usuari, 
    NivellIdioma, 
    FamiliaProfessional, 
    RegistreAuditoria
)

 

# --------------------------------------------------------------------------------------------
# OFERTA
#
# --------------------------------------------------------------------------------------------

#
#  Mostra el formulari per afegir una oferta
#
@login_required
def afegir_oferta(request):

    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        return redirect('index')
    
    # Recuperar totes les famílies professionals i precarregar els seus cicles associats
    # Utilitzem Prefetch per carregar els cicles de cada família de manera eficient
    # i els ordenem per nom, tant les famílies com els cicles dins de cada família.
    familias = FamiliaProfessional.objects.order_by('nom').prefetch_related(
        Prefetch(
            'cicle_set',  
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
    
    
    context = {
    'cicles': Cicle.objects.all(),
    'cicles_agrupats_per_familia': cicles_agrupats_per_familia,
    'capacitats': CapacitatClau.objects.all(),
    'TIPUS_CONTRACTE': Oferta.TIPUS_CONTRACTE,
    'JORNADA': Oferta.JORNADA,
    'PUBLIC_DESTINATARI': Oferta.PUBLIC_DESTINATARI,
    'EXPERIENCIA': Oferta.EXPERIENCIA,
    'current_page' : 'llista_ofertes'
    }
    return render(request, 'borsa_treball/afegir_oferta_empresa.html', context)

#
# Crear l'oferta : API
#


def validar_data(data_limit):
    """Valida el camp data_limit amb múltiples formats acceptats"""
    
    if not data_limit or data_limit.strip() == "":
        return "La data límit és obligatòria."
    
    # Formats acceptats
    formats = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d']
    
    for format_str in formats:
        try:
            datetime.strptime(data_limit.strip(), format_str)
            return None  # Data vàlida
        except ValueError:
            continue
    
    return "El format de la data no és vàlid. Utilitza DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY o YYYY/MM/DD."



@login_required
@require_POST
def crear_oferta_api(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'errors': {'global': 'Dades JSON no vàlides'}}, status=400)
    
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No tens permisos per accedir a aquesta pàgina.'})    

    errors = {}

    # Validacions amb variables locals
    titol = data.get('titol', '').strip()
    if not titol:
        errors['titol'] = "El títol és obligatori."

    data_limit = data.get('data_limit')
    error_data = validar_data(data_limit)  
    if error_data:
        errors['data_limit'] = error_data

    descripcio = data.get('descripcio', '').strip()
    if not descripcio:
        errors['descripcio'] = "La descripció és obligatòria."

    tipus_contracte = data.get('tipus_contracte', '').strip()
    if not tipus_contracte:
        errors['tipus_contracte'] = "Tipus de contracte obligatori."

    jornada = data.get('jornada', '').strip()
    if not jornada:
        errors['jornada'] = "Jornada obligatòria."

    lloc_treball = data.get('lloc_treball', '').strip()
    if not lloc_treball:
        errors['lloc_treball'] = "Lloc de treball obligatori."

    # Variables per camps opcionals
    destinatari = data.get('destinatari', 'AMB').strip()
    experiencia = data.get('experiencia', '').strip()
    requisits = data.get('requisits', '').strip()
    horari = data.get('horari', '').strip()
    salari = data.get('salari', '').strip()
    
    visible = data.get('visible', True)

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

    # Validació cicles amb verificació d'existència
    cicles_ids = data.get('cicles', [])
    if not cicles_ids:
        errors['cicles'] = "Has de seleccionar almenys un cicle."
    else:
        try:
            cicles_existents = Cicle.objects.filter(id__in=cicles_ids).count()
            if cicles_existents != len(cicles_ids):
                errors['cicles'] = "Alguns cicles seleccionats no existeixen."
        except Exception as e:
            errors['cicles'] = "Error validant els cicles seleccionats."

    # Validació capacitats clau amb verificació d'existència
    capacitats_ids = data.get('capacitats_clau', [])
    if capacitats_ids:
        try:
            capacitats_existents = CapacitatClau.objects.filter(id__in=capacitats_ids).count()
            if capacitats_existents != len(capacitats_ids):
                errors['capacitats_clau'] = "Algunes capacitats seleccionades no existeixen."
        except Exception as e:
            errors['capacitats_clau'] = "Error validant les capacitats seleccionades."

    if errors:
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    capacitats = data.get('capacitatsLliures', [])
   
    # Creació amb transacció
    try:
        with transaction.atomic():
            # Crear oferta amb variables validades

            estat_valor = 'RV' if visible else 'OC'  # 'En revisió' si visible, 'Oculta' si no

            oferta = Oferta.objects.create(
                empresa=empresa,
                titol=titol,
                descripcio=descripcio,
                data_limit=parse_date(data_limit) if data_limit and data_limit.strip() else None,
                tipus_contracte=tipus_contracte,
                jornada=jornada,
                hores_setmanals=hores_valor,  
                horari=horari,
                salari=salari,
                numero_vacants = vacants_valor,
                requisits=requisits,
                lloc_treball=lloc_treball,
                contacte_nom=empresa.nom_comercial,
                contacte_email=request.user.email,
                contacte_telefon=empresa.telefon or '',
                public_destinatari=destinatari,
                experiencia=experiencia,
                estat=estat_valor,
            )

            # Validació del model abans de continuar
            oferta.full_clean()

            # Relacions many-to-many amb variables validades
            oferta.cicles.set(cicles_ids)  
            if capacitats_ids:
                oferta.capacitats_clau.set(capacitats_ids)  


            
            for nom in capacitats:
                if nom.strip():
                    CapacitatOferta.objects.create(oferta=oferta, nom=nom.strip())
                    

            # Crear funcions
            for ordre, desc in enumerate(data.get('funcions', []), start=1):
                if desc.strip():
                    Funcio.objects.create(oferta=oferta, descripcio=desc.strip(), ordre=ordre)

            # Crear idiomes
            for idioma in data.get('idiomes', []):
                nom = idioma.get('nom', '').strip()
                nivell = idioma.get('nivell', '').strip()
                if nom and nivell:
                    NivellIdioma.objects.create(oferta=oferta, idioma=nom, nivell=nivell)

            # Log audit 
            RegistreAuditoria.objects.create(
                accio="Nova oferta",
                model_afectat="Oferta",
                descripcio=f"Oferta {oferta.titol} (Empresa: {oferta.empresa.nom_comercial} {oferta.empresa.cif}).",
                usuari=request.user
            )

    except ValidationError as e:
        return JsonResponse({
            'success': False, 
            'message': 'Error de validació del model',
            'errors': e.message_dict if hasattr(e, 'message_dict') else {'general': str(e)}
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': 'Error creant l\'oferta'
        }, status=500)

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
    
    today = timezone.now().date()
    
    ofertes = empresa.ofertes.all()
    
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    jornada_filter = request.GET.get('jornada', '')
    order_by = request.GET.get('order_by', '-data_publicacio')
    
    if search_query:
        ofertes = ofertes.filter(
            Q(titol__icontains=search_query) |
            Q(descripcio__icontains=search_query) |
            Q(lloc_treball__icontains=search_query)
        )
    
    if status_filter:
        if status_filter == 'activa':
            ofertes = ofertes.filter(estat='AC',data_limit__gte=today)
        elif status_filter == 'caducada':
            ofertes = ofertes.filter(data_limit__lt=today)
        elif status_filter == 'oculta':
            ofertes = ofertes.filter(estat='OC')
        elif status_filter == 'revisio':
            ofertes = ofertes.filter(estat='RV')
        elif status_filter == 'totes':
            pass  # No s'aplica cap filtre

    
    if type_filter:
        ofertes = ofertes.filter(tipus_contracte=type_filter)
    
    if jornada_filter:
        ofertes = ofertes.filter(jornada=jornada_filter)
        
    # Anotació amb el Count de candidatures ACTIVES
    ofertes = ofertes.annotate(
        candidatures_count=Count('candidatures', filter=Q(candidatures__activa=True))
    )
    

    # Ordenació
    valid_order_fields = [
        'data_publicacio', '-data_publicacio',
        'data_limit', '-data_limit',
        'titol', '-titol',
        'candidatures_count', '-candidatures_count' # Aquest camp ja existeix per ordenar
    ]
    
    if order_by in valid_order_fields:
        ofertes = ofertes.order_by(order_by)
    else:
        ofertes = ofertes.order_by('-data_publicacio')
    
    stats = {
        'total': empresa.ofertes.count(),
        'actives': empresa.ofertes.filter(data_limit__gte=today, estat='AC').count(),
        'caducades': empresa.ofertes.filter(data_limit__lt=today).count(),
        'ocultes': empresa.ofertes.filter(estat='OC').count(),
        'revisio': empresa.ofertes.filter(estat='RV').count(),
        'total_candidatures_actives': Candidatura.objects.filter(oferta__empresa=empresa, estat='AC').count(),
    }
    
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
    
    tipus_contracte_choices = Oferta.TIPUS_CONTRACTE
    jornada_choices = Oferta.JORNADA
    
    status_choices = [
        ('', 'Tots els estats'),
        ('activa', 'Actives'),
        ('caducada', 'Caducades'),
        ('oculta', 'Ocultes'),
        ('revisio', 'En revisió'),
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
        'current_page' : 'llista_ofertes'
    }
    
    return render(request, 'borsa_treball/llista_ofertes_empresa.html', context)

#
#  AMAGAR/MOSTRAR OFERTES: API 
#

@login_required
@require_http_methods(["POST"])
def toggle_visibilitat_oferta(request, oferta_id):
    """
    Vista per canviar l'estat de l'oferta: OC a RV
    """
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'No tens permisos per realitzar aquesta acció.'
        }, status=403)
    
    
    try:
        oferta = Oferta.objects.get(id=oferta_id, empresa=empresa)
    except Oferta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Oferta no trobada'}, status=404)
    
    try:
       
        if oferta.estat == 'AC':
            return JsonResponse({
                'success': False,
                'message': "No es pot modificar l'estat perquè l'oferta està activa.",
                'error_type': 'oferta_activa',                
            }, status=400)            
        else:
            if oferta.estat == 'OC':
                oferta.estat = 'RV'
            else:
                oferta.estat = 'OC'

        oferta.save()
        
        status_text = "en revisió" if oferta.estat == 'RV' else "oculta"
        
        return JsonResponse({
            'success': True,
            'message': f'L\'oferta "{oferta.titol}" ara és {status_text}.',
            'estat': oferta.estat,
            'oferta_id': oferta.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error en canviar l\'estat de l\'oferta: {str(e)}'
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
    try:
        oferta = Oferta.objects.get(id=oferta_id, empresa=empresa)
    except Oferta.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Oferta no trobada'}, status=404)
    
    try:
        if oferta.estat == 'AC':
            return JsonResponse({
                'success': False,
                'message': "No es pot esborrar l'oferta perquè aquesta està activa.",
                'error_type': 'oferta_activa',                
            }, status=400)   
        

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
# EDITAR OFERTA
#
@login_required
def editar_oferta(request, oferta_id):
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        messages.error(request, 'No tens permisos per accedir a aquesta pàgina.')
        return redirect('index')

    # oferta = get_object_or_404(Oferta, id=oferta_id, empresa=empresa)
    oferta = get_object_or_404(
        Oferta.objects.annotate(
            candidatures_count=Count('candidatures', filter=Q(candidatures__activa=True))
        ),
        id=oferta_id, 
        empresa=empresa
    )

    familias = FamiliaProfessional.objects.order_by('nom').prefetch_related(
        Prefetch(
            'cicle_set',  
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

    capacitats_lliures = list(oferta.capacitats.values_list('nom', flat=True))
    
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
        'capacitats_lliures_existents': capacitats_lliures,
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
        'current_page' : 'llista_ofertes'
    }

    return render(request, 'borsa_treball/editar_oferta_empresa.html', context)


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

    # Validar camps
    errors = {}
    
    # Validació títol
    titol = data.get('titol', '').strip()
    if not titol:
        errors['titol'] = "El títol és obligatori."

    # Validació data límit
    data_limit = data.get('data_limit')
    error_data = validar_data(data_limit)  
    if error_data:
        errors['data_limit'] = error_data

    # Validació descripció
    descripcio = data.get('descripcio', '').strip()
    if not descripcio:
        errors['descripcio'] = "La descripció és obligatòria."

    # Validació tipus contracte
    tipus_contracte = data.get('tipus_contracte', '').strip()
    if not tipus_contracte:
        errors['tipus_contracte'] = "Tipus de contracte obligatori."

    # Validació jornada
    jornada = data.get('jornada', '').strip()
    if not jornada:
        errors['jornada'] = "Jornada obligatòria."

    # Validació lloc treball
    lloc_treball = data.get('lloc_treball', '').strip()
    if not lloc_treball:
        errors['lloc_treball'] = "Lloc de treball obligatori."

    

    # Camps opcionals amb validació de format
    destinatari = data.get('destinatari', 'AMB').strip()
    experiencia = data.get('experiencia', '').strip()
    requisits = data.get('requisits', '').strip()
    horari = data.get('horari', '').strip()
    salari = data.get('salari', '').strip()

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

    
    # Validació cicles amb verificació d'existència
    cicles_ids = data.get('cicles', [])
    if not cicles_ids:
        errors['cicles'] = "Has de seleccionar almenys un cicle."
    else:
        try:
            # Verificar que tots els cicles existeixen
            cicles_existents = Cicle.objects.filter(id__in=cicles_ids).count()
            if cicles_existents != len(cicles_ids):
                errors['cicles'] = "Alguns cicles seleccionats no existeixen."
        except Exception as e:
            errors['cicles'] = "Error validant els cicles seleccionats."

    capacitats_ids = data.get('capacitats_clau', [])
    if capacitats_ids:
        try:
            capacitats_existents = CapacitatClau.objects.filter(id__in=capacitats_ids).count()
            if capacitats_existents != len(capacitats_ids):
                errors['capacitats_clau'] = "Algunes capacitats seleccionades no existeixen."
        except Exception as e:
            errors['capacitats_clau'] = "Error validant les capacitats seleccionades."

    

    if errors:
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    # Actualització amb transacció
    try:
        with transaction.atomic():
            # ASSIGNACIÓ VALORS VALIDATS
            oferta.titol = titol
            oferta.data_limit = data_limit if data_limit and data_limit.strip() else None
            oferta.numero_vacants = vacants_valor  
            oferta.descripcio = descripcio
            oferta.tipus_contracte = tipus_contracte
            oferta.jornada = jornada
            oferta.hores = hores_valor  
            oferta.horari = horari
            oferta.salari = salari
            oferta.requisits = requisits
            oferta.lloc_treball = lloc_treball
            oferta.public_destinatari = destinatari
            oferta.experiencia = experiencia                     
            oferta.numero_vacants = vacants_valor

            # Validació del model abans de desar
            oferta.full_clean()
            oferta.save()

            # Eliminar funcions antigues i afegir noves
            oferta.funcions.all().delete()
            for descripcio_funcio in data.get("funcions", []):
                if descripcio_funcio.strip():  # Validar que no sigui buit
                    Funcio.objects.create(oferta=oferta, descripcio=descripcio_funcio.strip())

            # Actualitzar relacions many-to-many
            oferta.cicles.set(cicles_ids)
            oferta.capacitats_clau.set(capacitats_ids)

            # Eliminar idiomes antics i afegir nous
            oferta.idiomes.all().delete()
            for idioma_data in data.get("idiomes", []):
                idioma_nom = idioma_data.get("idioma", "").strip()
                nivell = idioma_data.get("nivell", "").strip()
                if idioma_nom and nivell:  # Validar que no siguin buits
                    oferta.idiomes.create(idioma=idioma_nom, nivell=nivell)

    except ValidationError as e:
        return JsonResponse({
            'success': False, 
            'message': 'Error de validació de dades del model Oferta',
            'errors': e.message_dict if hasattr(e, 'message_dict') else {'general': str(e)}
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': 'Error actualitzant l\'oferta'
        }, status=500)
    
    return JsonResponse({'success': True, 'message': 'Oferta actualitzada correctament'})



# -----------------------------------------------------------------------------------------------------
# EDITAR PERFIL 
# -----------------------------------------------------------------------------------------------------

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
        'current_page' : 'editar_perfil'
    }
    return render(request, 'borsa_treball/editar_perfil_empresa.html', context)



# API per modificar informació de l'Empresa
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
    # Telefon no és obligatori 
    if telefon and not re.match(r'^\+?[0-9\s\-\(\)]{1,15}$', telefon):
        errors.setdefault('telefon', []).append('El telèfon no té un format vàlid (pot incloure "+" al principi, números, espais, guions i parèntesis; màxim 15 caràcters).')

    email_contacte = request.POST.get('email_contacte', '').strip()
    # Email de contacte no és obligatori
    if email_contacte:
        try:
            validate_email(email_contacte)
        except ValidationError:
            errors.setdefault('email_contacte', []).append('L\'email de contacte no té un format vàlid.')

    num_treballadors_str = request.POST.get('num_treballadors', '').strip()
    num_treballadors = None 
    # num_treballadors no és obligatori 
    if num_treballadors_str:
        try:
            num_treballadors = int(num_treballadors_str)
            if num_treballadors < 0:
                errors.setdefault('num_treballadors', []).append('El número de treballadors ha de ser positiu.')
        except ValueError:
            errors.setdefault('num_treballadors', []).append('El número de treballadors ha de ser un nombre enter.')

    sector_id = request.POST.get('sector', '')
    sector_obj = None
    # Sector no és obligatori 
    if sector_id:
        try:
            sector_obj = Sector.objects.get(id=sector_id)
        except Sector.DoesNotExist:
            errors.setdefault('sector', []).append('El sector seleccionat no és vàlid.')
    
    web = request.POST.get('web', '').strip()
    # Web no és obligatori 
    if web and not web.startswith(('http://', 'https://')):
        web = 'https://' + web
    # Validació de format d'URL bàsica
    if web and not re.match(r'^https?://[^\s/$.?#].[^\s]*$', web):
        errors.setdefault('web', []).append('La pàgina web no té un format vàlid.')
    
    descripcio = request.POST.get('descripcio', '').strip()
    # Descripcio no és obligatori 


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


# API canviar la informació del Contacte (Usuari) 
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
       
        empresa_associada = user_to_delete.empresa 
    except (Empresa.DoesNotExist, AttributeError):
        # Si no hi ha empresa associada o l'usuari no és de tipus empresa
        messages.error(request, 'No s\'ha trobat un perfil d\'empresa vàlid associat al teu usuari.')
        return redirect('index')
    
    try:
        # PRIMER: Tancar la sessió de l'usuari, abans d'eliminar el compte.
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


# --------------------------------------------------------------------------------------------------------
#  CANDIDATURES
#
# --------------------------------------------------------------------------------------------------------

@login_required
def candidatures_oferta(request, oferta_id):
    """
    Vista per veure les candidatures d'una oferta específica.
    """
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        messages.error(request, 'No tens permisos per accedir a aquesta pàgina.')
        return redirect('index')
    
    # Obtenir l'oferta i verificar que pertany a l'empresa
    oferta = get_object_or_404(Oferta, id=oferta_id, empresa=empresa)
    
    # Filtres
    estat_filtre = request.GET.get('estat', '')
    cerca = request.GET.get('cerca', '')
    ordenar = request.GET.get('ordenar', '-data_candidatura')
    
    # Obtenir candidatures i filtrar per 'activa=True'
   
    candidatures = oferta.candidatures.select_related('estudiant', 'estudiant__usuari').filter(activa=True)
   
    
    # Aplicar filtres
    if estat_filtre:
        candidatures = candidatures.filter(estat=estat_filtre)
    
    if cerca:
        candidatures = candidatures.filter(
            Q(estudiant__usuari__nom__icontains=cerca) |
            Q(estudiant__usuari__cognoms__icontains=cerca) |
            Q(estudiant__usuari__email__icontains=cerca)          
        )
    
    # Ordenar
    if ordenar == 'nom':
        candidatures = candidatures.order_by('estudiant__usuari__nom', 'estudiant__usuari__cognoms')
    elif ordenar == 'estat':
        candidatures = candidatures.order_by('estat', '-data_candidatura')
    elif ordenar == 'puntuacio':
        # Cal tenir en compte que si `puntuacio` és null, es posarà al principi/final segons el SGBD.
        # Podries voler ordenar els nuls al final si és el cas.
        candidatures = candidatures.order_by('-puntuacio', '-data_candidatura')
    else:
        candidatures = candidatures.order_by('-data_candidatura')
    
    # Paginació
    paginator = Paginator(candidatures, 10)
    page_number = request.GET.get('page')
    candidatures_page = paginator.get_page(page_number)
    
    # Estadístiques
    
    stats = oferta.candidatures.filter(activa=True).aggregate( 
        total=Count('id'),
        rebutjades=Count('id', filter=Q(estat=EstatCandidatura.REBUTJADA)),
        en_proces=Count('id', filter=Q(estat=EstatCandidatura.EN_PROCES)),
        preseleccionades=Count('id', filter=Q(estat=EstatCandidatura.PRESELECCIONADA)),
        entrevistes=Count('id', filter=Q(estat=EstatCandidatura.ENTREVISTA)),
        contratades=Count('id', filter=Q(estat=EstatCandidatura.CONTRATADA)),
    )
    
    # Calcular dies restants
    today = timezone.now().date()
    dies_restants = (oferta.data_limit - today).days if oferta.data_limit and oferta.data_limit > today else 0 
   
    
    context = {
        'oferta': oferta,
        'candidatures': candidatures_page,
        'stats': stats,
        'dies_restants': dies_restants,
        'estat_filtre': estat_filtre,
        'cerca': cerca,
        'ordenar': ordenar,
        'estats_choices': EstatCandidatura.choices,
        'today': today,
    }
    
    return render(request, 'borsa_treball/llista_candidatures_oferta.html', context)


@login_required
def veure_carta_presentacio(request, candidatura_id):
    """
    Vista AJAX per obtenir la carta de presentació d'una candidatura.
    """
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No tens permisos per accedir a aquesta pàgina.'})
    
    # Obtenir la candidatura i verificar permisos
    candidatura = get_object_or_404(Candidatura, id=candidatura_id, oferta__empresa=empresa)
    
    return JsonResponse({
        'success': True,
        'carta_presentacio': candidatura.carta_presentacio or 'No hi ha carta de presentació.',
        'estudiant_nom': candidatura.estudiant.usuari.get_full_name(),
        'data_candidatura': candidatura.data_candidatura.strftime('%d/%m/%Y %H:%M')
    })


@login_required
def descarregar_cv_candidatura(request, candidatura_id):
    """
    Vista per descarregar el CV d'una candidatura.
    """
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        messages.error(request, 'No tens permisos per accedir a aquesta pàgina.')
        return redirect('index')
    
    # Obtenir la candidatura i verificar permisos
    candidatura = get_object_or_404(Candidatura, id=candidatura_id, oferta__empresa=empresa)
    
    if not candidatura.cv_adjunt:
        raise Http404("CV no trobat")
    
    try:
        # Obtenir el fitxer
        file_path = candidatura.cv_adjunt.path
        
        if not os.path.exists(file_path):
            raise Http404("Fitxer no trobat")
        
        # Determinar el tipus MIME
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        # Crear la resposta
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=content_type)
            
        # Nom del fitxer per la descàrrega
        filename = f"CV_{candidatura.estudiant.usuari.get_full_name()}_{candidatura.oferta.titol}.pdf"
        filename = filename.replace(' ', '_').replace(',', '')
        
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        messages.error(request, f'Error en descarregar el CV: {str(e)}')
        return redirect('llista_candidatures_oferta', oferta_id=candidatura.oferta.id)
    


@login_required
def canviar_estat_candidatura(request, candidatura_id):
    """
    Vista AJAX per canviar l'estat d'una candidatura.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Mètode no permès'})
    
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No tens permisos per accedir a aquesta pàgina.'})
    
    # Obtenir la candidatura i verificar permisos
    candidatura = get_object_or_404(Candidatura, id=candidatura_id, oferta__empresa=empresa)
    
    nou_estat = request.POST.get('estat')
    if nou_estat not in [choice[0] for choice in EstatCandidatura.choices]:
        return JsonResponse({'success': False, 'error': 'Estat no vàlid'})
    
    try:
        candidatura.estat = nou_estat
        candidatura.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Estat canviat a "{candidatura.get_estat_display()}"',
            'nou_estat': nou_estat,
            'nou_estat_display': candidatura.get_estat_display()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error en canviar l\'estat: {str(e)}'})

