from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.utils import timezone
from .models import Oferta, Empresa, Cicle, Candidatura, Estudiant


def llista_ofertes_estudiants2(request):
   
    
    # Obtenir ofertes visibles i no caducades
    ofertes = Oferta.objects.filter(
        visible=True,
        data_limit__gte=timezone.now().date()
    ).select_related('empresa').prefetch_related('cicles', 'candidatures')
    
    # Filtres
    cerca = request.GET.get('cerca', '')
    empresa_id = request.GET.get('empresa', '')
    cicle_id = request.GET.get('cicle', '')
    tipus_contracte = request.GET.get('tipus_contracte', '')
    jornada = request.GET.get('jornada', '')
    ordenar = request.GET.get('ordenar', '-data_publicacio')
    
    # Aplicar filtres
    if cerca:
        ofertes = ofertes.filter(
            Q(titol__icontains=cerca) |
            Q(descripcio__icontains=cerca) |
            Q(lloc_treball__icontains=cerca) |
            Q(empresa__nom_comercial__icontains=cerca)
        )
    
    if empresa_id:
        ofertes = ofertes.filter(empresa_id=empresa_id)
    
    if cicle_id:
        ofertes = ofertes.filter(cicles__id=cicle_id)
    
    if tipus_contracte:
        ofertes = ofertes.filter(tipus_contracte=tipus_contracte)
    
    if jornada:
        ofertes = ofertes.filter(jornada=jornada)
    
    # Ordenació
    if ordenar == 'titol':
        ofertes = ofertes.order_by('titol')
    elif ordenar == 'empresa':
        ofertes = ofertes.order_by('empresa__nom_comercial')
    elif ordenar == 'data_limit':
        ofertes = ofertes.order_by('data_limit')
    elif ordenar == '-data_limit':
        ofertes = ofertes.order_by('-data_limit')
    elif ordenar == 'lloc_treball':
        ofertes = ofertes.order_by('lloc_treball')
    else:  # -data_publicacio (per defecte)
        ofertes = ofertes.order_by('-data_publicacio')
    
    # Eliminar duplicats si hi ha filtres per cicles
    if cicle_id:
        ofertes = ofertes.distinct()
    
   
    
    # Paginació
    paginator = Paginator(ofertes, 12)  # 12 ofertes per pàgina
    page = request.GET.get('page')
    
    try:
        ofertes_paginades = paginator.page(page)
    except PageNotAnInteger:
        ofertes_paginades = paginator.page(1)
    except EmptyPage:
        ofertes_paginades = paginator.page(paginator.num_pages)
    
    # Dades per filtres
    empreses = Empresa.objects.filter(
        ofertes__visible=True,
        ofertes__data_limit__gte=timezone.now().date()
    ).distinct().order_by('nom_comercial')
    
    cicles = Cicle.objects.filter(
        ofertes__visible=True,
        ofertes__data_limit__gte=timezone.now().date()
    ).distinct().order_by('nom')
    
    # Estadístiques
    total_ofertes = ofertes.count()
 
   
    
    context = {
        'ofertes': ofertes_paginades,       
        'empreses': empreses,
        'cicles': cicles,
        'cerca': cerca,
        'empresa_seleccionada': empresa_id,
        'cicle_seleccionat': cicle_id,
        'tipus_contracte_seleccionat': tipus_contracte,
        'jornada_seleccionada': jornada,
        'ordenar': ordenar,
        'total_ofertes': total_ofertes,
      
      
        'tipus_contracte_choices': Oferta.TIPUS_CONTRACTE,
        'jornada_choices': Oferta.JORNADA,
    }
    
    return render(request, 'borsa_treball/tauler_ofertes.html', context)



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime
from django.core.paginator import Paginator

from .models import Oferta, Empresa, Cicle, Funcio, NivellIdioma, CapacitatClau # Make sure you import Cicle


def llista_ofertes_estudiants(request):
    """
    Vista pública per llistar ofertes de feina actives i visibles.
    Calcula els dies restants per a cada oferta.
    Permet filtrar per Cicle (estudis).
    """
    # Filtrem les ofertes que són visibles i actives
    # Si vols mostrar nom només ofertes futures, afegeix: data_limit__gte=timezone.now().date()
    ofertes_queryset = Oferta.objects.filter(
        visible=True,
        activa=True
    ).order_by('-data_publicacio')

    # Get all Cicles for the filter dropdown
    cicles = Cicle.objects.all().order_by('nom')

    # Apply filter by Cicle if selected
    cicle_id = request.GET.get('cicle_id')
    if cicle_id:
        ofertes_queryset = ofertes_queryset.filter(cicles__id=cicle_id)

    ofertes_amb_dies_restants = []
    today = timezone.now().date() # Obtenim la data actual sense hora per a la comparació

    for oferta in ofertes_queryset:
        days_remaining = None
        if oferta.data_limit:
            if oferta.data_limit < today:
                days_remaining = -1 # Indica que l'oferta ha caducat
            else:
                # Calculem la diferència en dies
                diff = oferta.data_limit - today
                days_remaining = diff.days # Aquest és el nombre de dies com a enter

        # Afegim el nombre de dies restants com a atribut a l'objecte oferta
        # per poder-lo usar directament a la plantilla.
        oferta.days_remaining = days_remaining
        ofertes_amb_dies_restants.append(oferta)

    # Paginació
    paginator = Paginator(ofertes_amb_dies_restants, 10) # 10 ofertes per pàgina
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'ofertes': page_obj,
        'cicles': cicles,  # Pass the list of Cicles to the template
        'selected_cicle': int(cicle_id) if cicle_id else None, # Pass the selected cicle_id back
        'user': request.user, # Passem l'objecte usuari per la lògica d'autenticació
        # No cal passar 'now' si ja calculem 'days_remaining' a la vista
    }
    return render(request, 'borsa_treball/tauler_ofertes.html', context)



def detall_oferta_tauler(request, oferta_id):
    """
    Vista per veure els detalls complets d'una oferta.
    """
    
    
    # Obtenir l'oferta i verificar que pertany a l'empresa
    oferta = get_object_or_404(Oferta, id=oferta_id)
    
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
    
    return render(request, 'borsa_treball/detall_oferta_tauler.html', context)



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from datetime import datetime
import json
import re # For DNI validation if needed

# Import your models
from .models import Usuari, Estudiant, Cicle, EstudiEstudiant, RegistreAuditoria # Add any others you need

@login_required
def perfil_estudiant(request):
    """
    Renders the student profile page.
    """
    if request.user.tipus != 'EST':
        # Redirect non-student users from this page
        # You might want a more specific redirect or error message
        return redirect('index') # Or 'some_error_page'

    estudiant = request.user.estudiant # Get the related Estudiant object
    cicles = Cicle.objects.all().order_by('nom') # Get all cycles for the dropdown

    context = {
        'estudiant': estudiant,
        'cicles': cicles,
        'current_year': datetime.now().year,
        'current_page': 'editar_perfil' 
    }
    return render(request, 'borsa_treball/editar_perfil_estudiant.html', context)

@login_required
@require_POST
def api_actualitzar_perfil_estudiant(request):
    """
    API endpoint to update student's user and student profile data.
    """
    if request.user.tipus != 'EST':
        return JsonResponse({'success': False, 'message': 'Accés no autoritzat.'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Dades de petició no vàlides (JSON mal format).'}, status=400)

    user = request.user
    estudiant = user.estudiant
    errors = {}

    # Get data from request
    nom = data.get('nom', '').strip()
    cognoms = data.get('cognoms', '').strip()
    email = data.get('email', '').strip()
    telefon = data.get('telefon', '').strip()
    dni = data.get('dni', '').strip()
    carnet_conduir = data.get('carnet_conduir', False) # This will be a boolean

    # Validate fields
    if not nom: errors['nom'] = ['El nom és obligatori.']
    if not cognoms: errors['cognoms'] = ['Els cognoms són obligatoris.']
    if not telefon: errors['telefon'] = ['El telèfon és obligatori.']

    if not email:
        errors['email'] = ['El correu electrònic és obligatori.']
    elif Usuari.objects.filter(email=email).exclude(id=user.id).exists(): # Check if email is taken by another user
        errors['email'] = ['Aquest correu electrònic ja està registrat per un altre usuari.']

    if not dni:
        errors['dni'] = ['El DNI és obligatori.']
    else:
        dni_pattern = r'^\d{8}[A-Z]$'
        if not re.match(dni_pattern, dni):
            errors['dni'] = ['Format de DNI no vàlid. Ha de ser 8 dígits seguits d\'una lletra (ex: 12345678A).']
        elif Estudiant.objects.filter(dni=dni).exclude(pk=estudiant.pk).exists(): # Check if DNI is taken by another student
            errors['dni'] = ['Aquest DNI ja està registrat per un altre estudiant.']


    if errors:
        return JsonResponse({'success': False, 'message': 'Si us plau, corregeix els errors del formulari.', 'errors': errors}, status=400)

    try:
        with transaction.atomic():
            # Update Usuari fields
            user.nom = nom
            user.cognoms = cognoms
            user.email = email
            user.telefon = telefon
            user.save()

            # Update Estudiant fields
            estudiant.dni = dni
            estudiant.carnet_conduir = carnet_conduir
            estudiant.save()

            # Log audit (optional)
            RegistreAuditoria.objects.create(
                accio="Actualització Perfil Estudiant",
                model_afectat="Estudiant",
                descripcio=f"Estudiant {user.get_full_name()} (ID: {user.id}) ha actualitzat el seu perfil.",
                usuari=user
            )

        return JsonResponse({
            'success': True,
            'message': 'Perfil actualitzat correctament!',
            'nom': user.nom,
            'cognoms': user.cognoms
        })

    except Exception as e:
        print(f"Error al guardar perfil estudiant: {e}")
        return JsonResponse({'success': False, 'message': 'Error intern del servidor al guardar el perfil.'}, status=500)

@login_required
@require_POST
def api_afegir_estudi_estudiant(request):
    """
    API endpoint to add a new EstudiEstudiant for the current student.
    """
    if request.user.tipus != 'EST':
        return JsonResponse({'success': False, 'message': 'Accés no autoritzat.'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Dades de petició no vàlides (JSON mal format).'}, status=400)

    estudiant = request.user.estudiant
    errors = {}

    cicle_id = data.get('cicle')
    any_inici_str = str(data.get('any_inici') or '').strip()
    any_fi_str = str(data.get('any_fi') or '').strip()
    centre_estudis = str(data.get('centre_estudis') or '').strip() # També aplicat per seguretat


    # Validate cicle
    cicle_obj = None
    if not cicle_id:
        errors['cicle'] = ['El cicle formatiu és obligatori.']
    else:
        try:
            cicle_obj = Cicle.objects.get(id=int(cicle_id))
        except (ValueError, Cicle.DoesNotExist):
            errors['cicle'] = ['El cicle formatiu seleccionat no és vàlid o no existeix.']

    # Validate years (similar to registre_estudiant)
    any_inici = None
    any_fi = None

    if not any_inici_str:
        errors['any_inici'] = ['L\'any d\'inici és obligatori.']
    else:
        try:
            any_inici = int(any_inici_str)
        except ValueError:
            errors['any_inici'] = ['L\'any d\'inici ha de ser un número sencer vàlid.']
        else:
            if any_inici > datetime.now().year:
                errors['any_inici'] = ['L\'any d\'inici no pot ser futur.']
            elif any_inici < 1900: 
                errors['any_inici'] = ['L\'any d\'inici és massa antic.']

    if any_fi_str:
        try:
            any_fi = int(any_fi_str)
        except ValueError:
            errors['any_fi'] = ['L\'any de finalització ha de ser un número sencer vàlid.']

    if any_inici is not None and any_fi is not None:
        if any_fi <= any_inici:
            errors['any_fi'] = ['L\'any de finalització ha de ser posterior a l\'any d\'inici.']

    if errors:
        return JsonResponse({'success': False, 'message': 'Si us plau, corregeix els errors del formulari.', 'errors': errors}, status=400)

    try:
        # Check for unique_together constraint manually before saving to provide a specific error
        if EstudiEstudiant.objects.filter(estudiant=estudiant, cicle=cicle_obj, any_inici=any_inici).exists():
            errors['general'] = ['Ja existeix un registre d\'estudis amb aquest cicle i any d\'inici.']
            return JsonResponse({'success': False, 'message': 'Aquest estudi ja està registrat.', 'errors': errors}, status=400)


        estudi_nou = EstudiEstudiant.objects.create(
            estudiant=estudiant,
            cicle=cicle_obj,
            any_inici=any_inici,
            any_fi=any_fi,
            centre_estudis=centre_estudis if centre_estudis else None
        )

        RegistreAuditoria.objects.create(
            accio="Afegir Estudi Estudiant",
            model_afectat="EstudiEstudiant",
            descripcio=f"Estudiant {estudiant.usuari.get_full_name()} ha afegit nou estudi: {cicle_obj.nom} ({any_inici}-{any_fi or 'Actual'})",
            usuari=request.user
        )

        return JsonResponse({
            'success': True,
            'message': 'Estudi afegit correctament!',
            'estudi_id': estudi_nou.id,
            'cicle_nom': estudi_nou.cicle.nom,
            'any_inici': estudi_nou.any_inici,
            'any_fi': estudi_nou.any_fi,
            'centre_estudis': estudi_nou.centre_estudis
        }, status=201)

    except Exception as e:
        print(f"Error afegint estudi: {e}")
        return JsonResponse({'success': False, 'message': 'Error intern del servidor al afegir l\'estudi.'}, status=500)

@login_required
@require_POST # Can also be @require_http_methods(['DELETE']) if you use HTTP DELETE
def api_esborrar_estudi_estudiant(request, estudi_id):
    """
    API endpoint to delete an EstudiEstudiant record.
    """
    if request.user.tipus != 'EST':
        return JsonResponse({'success': False, 'message': 'Accés no autoritzat.'}, status=403)

    estudiant = request.user.estudiant

    try:
        estudi = get_object_or_404(EstudiEstudiant, id=estudi_id, estudiant=estudiant)
        cicle_nom = estudi.cicle.nom # Get name before deleting for audit log
        estudi.delete()

        RegistreAuditoria.objects.create(
            accio="Esborrar Estudi Estudiant",
            model_afectat="EstudiEstudiant",
            descripcio=f"Estudiant {estudiant.usuari.get_full_name()} ha esborrat l'estudi: {cicle_nom} (ID: {estudi_id})",
            usuari=request.user
        )

        return JsonResponse({'success': True, 'message': 'Estudi eliminat correctament!'})
    except Exception as e:
        print(f"Error esborrant estudi: {e}")
        return JsonResponse({'success': False, 'message': 'Error intern del servidor al eliminar l\'estudi.'}, status=500)

# Assumed existing canviar_contrasenya_api or similar
# from django.contrib.auth import update_session_auth_hash # Needed if changing password logs user out

# @login_required
# @require_POST
# def canviar_contrasenya_api(request):
#     try:
#         data = json.loads(request.body)
#     except json.JSONDecodeError:
#         return JsonResponse({'success': False, 'message': 'Dades de petició no vàlides (JSON mal format).'}, status=400)

#     user = request.user
#     old_password = data.get('old_password')
#     new_password1 = data.get('new_password1')
#     new_password2 = data.get('new_password2')

#     errors = {}

#     if not user.check_password(old_password):
#         errors['old_password'] = ['La contrasenya actual no és correcta.']

#     if new_password1 != new_password2:
#         errors['new_password2'] = ['Les noves contrasenyes no coincideixen.']

#     try:
#         validate_password(new_password1, user=user)
#     except ValidationError as e:
#         errors['new_password1'] = list(e.messages)

#     if errors:
#         return JsonResponse({'success': False, 'message': 'Si us plau, corregeix els errors.', 'errors': errors}, status=400)

#     try:
#         user.set_password(new_password1)
#         user.save()
#         update_session_auth_hash(request, user) # To keep the user logged in
#         RegistreAuditoria.objects.create(
#             accio="Canvi Contrasenya",
#             model_afectat="Usuari",
#             descripcio=f"Usuari {user.email} ha canviat la seva contrasenya.",
#             usuari=user
#         )
#         return JsonResponse({'success': True, 'message': 'La contrasenya s\'ha canviat correctament.'})
#     except Exception as e:
#         print(f"Error canviant contrasenya: {e}")
#         return JsonResponse({'success': False, 'message': 'Error intern del servidor al canviar la contrasenya.'}, status=500)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.utils import timezone
from .models import Oferta, Empresa, Cicle, Candidatura, Estudiant

@login_required
def llista_ofertes_estudiants_auth(request):
    """
    Vista per mostrar ofertes disponibles als estudiants amb filtres i paginació.
    """
    try:
        estudiant = request.user.estudiant
    except Estudiant.DoesNotExist:
        messages.error(request, 'No tens permisos per accedir a aquesta pàgina.')
        return redirect('index')
    
    # Obtenir ofertes visibles i no caducades
    ofertes = Oferta.objects.filter(
        visible=True,
        data_limit__gte=timezone.now().date()
    ).select_related('empresa').prefetch_related('cicles', 'candidatures')
    
    # Filtres
    cerca = request.GET.get('cerca', '')
    empresa_id = request.GET.get('empresa', '')
    cicle_id = request.GET.get('cicle', '')
    tipus_contracte = request.GET.get('tipus_contracte', '')
    jornada = request.GET.get('jornada', '')
    ordenar = request.GET.get('ordenar', '-data_publicacio')
    
    # Aplicar filtres
    if cerca:
        ofertes = ofertes.filter(
            Q(titol__icontains=cerca) |
            Q(descripcio__icontains=cerca) |
            Q(lloc_treball__icontains=cerca) |
            Q(empresa__nom_comercial__icontains=cerca)
        )
    
    if empresa_id:
        ofertes = ofertes.filter(empresa_id=empresa_id)
    
    if cicle_id:
        ofertes = ofertes.filter(cicles__id=cicle_id)
    
    if tipus_contracte:
        ofertes = ofertes.filter(tipus_contracte=tipus_contracte)
    
    if jornada:
        ofertes = ofertes.filter(jornada=jornada)
    
    # Ordenació
    if ordenar == 'titol':
        ofertes = ofertes.order_by('titol')
    elif ordenar == 'empresa':
        ofertes = ofertes.order_by('empresa__nom_comercial')
    elif ordenar == 'data_limit':
        ofertes = ofertes.order_by('data_limit')
    elif ordenar == '-data_limit':
        ofertes = ofertes.order_by('-data_limit')
    elif ordenar == 'lloc_treball':
        ofertes = ofertes.order_by('lloc_treball')
    else:  # -data_publicacio (per defecte)
        ofertes = ofertes.order_by('-data_publicacio')
    
    # Eliminar duplicats si hi ha filtres per cicles
    if cicle_id:
        ofertes = ofertes.distinct()
    
    # Obtenir candidatures existents de l'estudiant
    candidatures_existents = set(
        Candidatura.objects.filter(estudiant=estudiant)
        .values_list('oferta_id', flat=True)
    )
    
    # Paginació
    paginator = Paginator(ofertes, 12)  # 12 ofertes per pàgina
    page = request.GET.get('page')
    
    try:
        ofertes_paginades = paginator.page(page)
    except PageNotAnInteger:
        ofertes_paginades = paginator.page(1)
    except EmptyPage:
        ofertes_paginades = paginator.page(paginator.num_pages)
    
    # Dades per filtres
    empreses = Empresa.objects.filter(
        ofertes__visible=True,
        ofertes__data_limit__gte=timezone.now().date()
    ).distinct().order_by('nom_comercial')
    
    cicles = Cicle.objects.filter(
        ofertes__visible=True,
        ofertes__data_limit__gte=timezone.now().date()
    ).distinct().order_by('nom')
    
    # Estadístiques
    total_ofertes = ofertes.count()
    ofertes_amb_candidatura = len([o for o in ofertes if o.id in candidatures_existents])
    ofertes_sense_candidatura = total_ofertes - ofertes_amb_candidatura
    
    context = {
        'ofertes': ofertes_paginades,
        'candidatures_existents': candidatures_existents,
        'empreses': empreses,
        'cicles': cicles,
        'cerca': cerca,
        'empresa_seleccionada': empresa_id,
        'cicle_seleccionat': cicle_id,
        'tipus_contracte_seleccionat': tipus_contracte,
        'jornada_seleccionada': jornada,
        'ordenar': ordenar,
        'total_ofertes': total_ofertes,
        'ofertes_amb_candidatura': ofertes_amb_candidatura,
        'ofertes_sense_candidatura': ofertes_sense_candidatura,
        'tipus_contracte_choices': Oferta.TIPUS_CONTRACTE,
        'jornada_choices': Oferta.JORNADA,
    }
    
    return render(request, 'borsa_treball/llista_ofertes_estudiant.html', context)


@login_required
def detall_oferta_estudiant(request, oferta_id):
    """
    Vista per veure els detalls d'una oferta des de la perspectiva de l'estudiant.
    """
    try:
        estudiant = request.user.estudiant
    except Estudiant.DoesNotExist:
        messages.error(request, 'No tens permisos per accedir a aquesta pàgina.')
        return redirect('index')
    
    # Obtenir l'oferta visible i no caducada
    oferta = get_object_or_404(
        Oferta,
        id=oferta_id,
        visible=True,
        data_limit__gte=timezone.now().date()
    )
    
    # Verificar si ja té candidatura
    candidatura_existent = Candidatura.objects.filter(
        oferta=oferta,
        estudiant=estudiant
    ).first()
    
    # Calcular dies restants
    today = timezone.now().date()
    dies_restants = (oferta.data_limit - today).days
    
    context = {
        'oferta': oferta,
        'candidatura_existent': candidatura_existent,
        'dies_restants': dies_restants,
        'today': today,
    }
    
    return render(request, 'borsa_treball/detall_oferta_estudiant.html', context)
