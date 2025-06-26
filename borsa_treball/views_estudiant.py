import mimetypes
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.utils import timezone
from .models import Oferta, Empresa, Cicle, Candidatura, Estudiant, EstatCandidatura

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime
from django.core.paginator import Paginator

from .models import Oferta, Empresa, Cicle, Funcio, NivellIdioma, CapacitatClau 


def llista_ofertes_tauler(request):
    """
    Vista pública per llistar ofertes de feina actives i no caducades.
    Calcula els dies restants per a cada oferta.
    Permet filtrar per Cicle (estudis).
    """
    # Filtrem les ofertes que són actives i futures (no caducades)   
    ofertes_queryset = Oferta.objects.filter(
        estat='AC',        
        data_limit__gte=timezone.now().date()
    ).order_by('-data_publicacio', 'data_limit')

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
       
    
    context = {
        'oferta': oferta,
        'dies_restants': dies_restants,       
        'today': today,
    }
    
    return render(request, 'borsa_treball/detall_oferta_tauler.html', context)



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
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
    
    # Obtenir ofertes actives i no caducades
    ofertes = Oferta.objects.filter(
        estat='AC',
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
        ofertes__estat='AC',
        ofertes__data_limit__gte=timezone.now().date()
    ).distinct().order_by('nom_comercial')
    
    cicles = Cicle.objects.filter(
        ofertes__estat='AC',
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
        'current_page' : 'llista_ofertes'
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
    
    # Obtenir l'oferta activa i no caducada
    oferta = get_object_or_404(
        Oferta,
        id=oferta_id,
        estat='AC',
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



@login_required
def afegir_candidatura(request, oferta_id):
    # Obtenir l'estudiant loguejat
    try:
        estudiant = request.user.estudiant
    except:
        # Redirigir si l'usuari no és un estudiant o hi ha algun problema
        return redirect('index') 
    
    # Obtenir l'oferta
    oferta = get_object_or_404(Oferta, pk=oferta_id, estat='AC')
    
    # Verificar si ja existeix candidatura
    if Candidatura.objects.filter(oferta=oferta, estudiant=estudiant).exists():
        # Pots afegir un missatge de flaix aquí per informar a l'usuari
        return redirect('llista_candidatures_estudiant') 

    errors = {}
    carta_presentacio_data = '' # Per mantenir la carta si hi ha errors

    if request.method == 'POST':
        carta_presentacio = request.POST.get('carta_presentacio', '').strip()
        cv_adjunt = request.FILES.get('cv_adjunt', None)
        
        # --- Validació de servidor ---
        
        # Validació de la carta de presentació
        if not carta_presentacio:
            errors['carta_presentacio'] = "La carta de presentació és obligatòria."
        elif len(carta_presentacio) < 50:
            errors['carta_presentacio'] = f"La carta de presentació ha de tenir un mínim de 50 caràcters. Actualment té {len(carta_presentacio)}."
        elif len(carta_presentacio) > 2000:
            errors['carta_presentacio'] = f"La carta de presentació no pot excedir els 2000 caràcters. Actualment té {len(carta_presentacio)}."
        
        # Guardar la carta_presentacio per si hi ha errors i es vol mantenir
        carta_presentacio_data = carta_presentacio

        # Validació del CV adjunt
        if not cv_adjunt:
            errors['cv_adjunt'] = "Heu d'adjuntar el vostre Currículum Vitae."
        else:
            # Validar tipus de fitxer (extensió)
            valid_extensions = ['.pdf', '.doc', '.docx']
            ext = os.path.splitext(cv_adjunt.name)[1].lower()
            if ext not in valid_extensions:
                errors['cv_adjunt'] = "Format de fitxer no vàlid. Només s'accepten PDF, DOC i DOCX."
            
            # Validar mida del fitxer (5MB = 5 * 1024 * 1024 bytes)
            max_size_mb = 5
            max_size_bytes = max_size_mb * 1024 * 1024
            if cv_adjunt.size > max_size_bytes:
                errors['cv_adjunt'] = f"El fitxer és massa gran. La mida màxima permesa és de {max_size_mb}MB."
        
        # Si no hi ha errors, crear la candidatura
        if not errors:
            Candidatura.objects.create(
                oferta=oferta,
                estudiant=estudiant,
                carta_presentacio=carta_presentacio,
                cv_adjunt=cv_adjunt,        
                estat='EP'  # En procés
            )
            # Pots afegir un missatge de flaix d'èxit aquí
            return redirect('llista_candidatures_estudiant')
    
    # Si hi ha errors o és un GET request, renderitzar el formulari amb els errors
    context = {
        'oferta': oferta,
        'errors': errors,
        'carta_presentacio': carta_presentacio_data, # Passar la carta per mantenir el text al formulari
    }
    return render(request, 'borsa_treball/afegir_candidatura.html', context)




@login_required
def llista_candidatures_estudiant(request):
    """Vista per llistar les candidatures de l'estudiant loggejat"""
    candidatures = Candidatura.objects.filter(
        estudiant=request.user.estudiant
    ).select_related('oferta', 'oferta__empresa').order_by('-data_candidatura')
    
    # Filtres
    estat_filter = request.GET.get('estat')
   
    cerca = request.GET.get('cerca', '')
    
    if estat_filter:
        candidatures = candidatures.filter(estat=estat_filter)
    
    if cerca:
        candidatures = candidatures.filter(
            Q(oferta__titol__icontains=cerca) |
            Q(oferta__empresa__nom_comercial__icontains=cerca) |
            Q(oferta__descripcio__icontains=cerca)
        )
    
    # Estadístiques
    stats = {
        'total': candidatures.count(),
        'en_proces': candidatures.filter(estat=EstatCandidatura.EN_PROCES).count(),
        'preseleccionades': candidatures.filter(estat=EstatCandidatura.PRESELECCIONADA).count(),
        'entrevistes': candidatures.filter(estat=EstatCandidatura.ENTREVISTA).count(),
        'contratades': candidatures.filter(estat=EstatCandidatura.CONTRATADA).count(),
        'rebutjades': candidatures.filter(estat=EstatCandidatura.REBUTJADA).count(),
    }
    
    # Paginació
    paginator = Paginator(candidatures, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'candidatures': page_obj,
        'stats': stats,
        'estats': EstatCandidatura.choices,
        'estat_filter': estat_filter,
        'cerca': cerca ,
        'current_page':'candidatures',
    }
    
    return render(request, 'borsa_treball/llista_candidatures_estudiant.html', context)


@login_required
def editar_candidatura_estudiant(request, candidatura_id):
    """Vista per editar una candidatura sense Django forms"""
   
    try:
        estudiant = request.user.estudiant
    except Estudiant.DoesNotExist:
        messages.error(request, 'No tens permisos per accedir a aquesta pàgina.')
        return redirect('index')
    


    candidatura = get_object_or_404(
        Candidatura,
        id=candidatura_id,
        estudiant=request.user.estudiant
    )
    
   
    
    if request.method == 'POST':

        # Només es pot editar si està en procés
        if candidatura.estat != EstatCandidatura.EN_PROCES:
            messages.error(request, 'No pots editar aquesta candidatura.')
            return redirect('llista_candidatures_estudiant')
    

        # Obtenir dades del formulari
        carta_presentacio = request.POST.get('carta_presentacio', '').strip()
        cv_adjunt = request.FILES.get('cv_adjunt')
        altres_adjunts = request.FILES.get('altres_adjunts')
        
        # Validacions
        errors = {}
        
        # Validar carta de presentació
        if not carta_presentacio:
            errors['carta_presentacio'] = 'La carta de presentació és obligatòria'
        elif len(carta_presentacio) < 50:
            errors['carta_presentacio'] = 'La carta ha de tenir almenys 50 caràcters'
        elif len(carta_presentacio) > 2000:
            errors['carta_presentacio'] = 'La carta no pot superar els 2000 caràcters'
        
        # Validar CV si s'ha pujat
        if cv_adjunt:
            if cv_adjunt.size > 5 * 1024 * 1024:  # 5MB
                errors['cv_adjunt'] = 'El CV no pot superar els 5MB'
            
            allowed_types = ['application/pdf', 'application/msword', 
                           'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
            if cv_adjunt.content_type not in allowed_types:
                errors['cv_adjunt'] = 'Format no vàlid. Només PDF, DOC o DOCX'
        
        # Validar altres adjunts si s'han pujat
        if altres_adjunts:
            if altres_adjunts.size > 10 * 1024 * 1024:  # 10MB
                errors['altres_adjunts'] = 'Els altres documents no poden superar els 10MB'
        
        # Si no hi ha errors, guardar
        if not errors:
            candidatura.carta_presentacio = carta_presentacio
            
            if cv_adjunt:
                candidatura.cv_adjunt = cv_adjunt
            
            if altres_adjunts:
                candidatura.altres_adjunts = altres_adjunts
            
            candidatura.save()
            messages.success(request, 'Candidatura actualitzada correctament!')
            return redirect('llista_candidatures_estudiant')
        else:
            # Afegir errors als missatges
            for field, error in errors.items():
                messages.error(request, error)
    
    context = {
        'candidatura': candidatura,
        'today': timezone.now().date(),
    }
    
    return render(request, 'borsa_treball/editar_candidatura_estudiant.html', context)


@login_required
def descarregar_cv_candidatura(request, candidatura_id):
    """
    Vista per descarregar el CV d'una candidatura.
    """
    try:
        estudiant = request.user.estudiant
    except Estudiant.DoesNotExist:
        #return HttpResponse('sense permisos')
        #messages.error(request, 'No tens permisos per accedir a aquesta pàgina.')
        return redirect('index')
    
    # Obtenir la candidatura i verificar permisos
    candidatura = get_object_or_404(Candidatura, id=candidatura_id)
    
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
        #return HttpResponse(f'Error en descarregar el CV: {str(e)}')
        #messages.error(request, f'Error en descarregar el CV: {str(e)}')
        return redirect('candidatures_oferta', oferta_id=candidatura.oferta.id)


@login_required
@require_POST
def eliminar_candidatura_api(request, candidatura_id):
    """
    Vista API per eliminar una candidatura.
    Retorna JsonResponse amb missatges i codis d'estat HTTP.
    """
    try:
        # Comprovar si l'usuari és un estudiant.
        # Si no ho és, no hauria de poder eliminar candidatures d'estudiant.
        # Això pot llançar Estudiant.DoesNotExist si no hi ha un perfil d'estudiant associat.
        estudiant = request.user.estudiant 
    except Estudiant.DoesNotExist:
        # L'usuari loggejat no té un perfil d'estudiant.
        return JsonResponse(
            {'error': 'Accés denegat. No estàs associat a un perfil d\'estudiant.'},
            status=403 # Forbidden
        )
    
    try:
        candidatura = get_object_or_404(
            Candidatura,
            id=candidatura_id,
            estudiant=estudiant # Assegura que només pot eliminar les seves pròpies candidatures
        )
    except Exception: # Pot capturar Http404 de get_object_or_404 o altres errors
        return JsonResponse(
            {'error': 'Candidatura no trobada o no tens permís per accedir-hi.'},
            status=404 # Not Found
        )
    
    # Verificar que es pot eliminar segons el seu estat
    if candidatura.estat not in [EstatCandidatura.EN_PROCES, EstatCandidatura.REBUTJADA]:
        return JsonResponse(
            {'error': 'No es pot eliminar aquesta candidatura en el seu estat actual.'},
            status=400 # Bad Request
        )
    
    try:
        candidatura.delete()
        return JsonResponse(
            {'message': 'Candidatura eliminada correctament.'},
            status=200 # OK
        )
    except Exception as e:
        # Capturar qualsevol altre error durant l'eliminació (p.ex., error de base de dades)
        return JsonResponse(
            {'error': f'Error intern del servidor al eliminar la candidatura: {str(e)}'},
            status=500 # Internal Server Error
        )


@login_required
@require_http_methods(["POST"])
def editar_candidatura_api(request, candidatura_id):
    """
    API endpoint to edit a 'candidatura' and return JSON with validation errors.
    """
    errors = {}

    try:
        estudiant = request.user.estudiant
    except Estudiant.DoesNotExist:
        return JsonResponse(
            {'error': 'No tens permisos per accedir a aquesta pàgina.'},
            status=403
        )

    candidatura = get_object_or_404(
        Candidatura,
        id=candidatura_id,
        estudiant=request.user.estudiant
    )

    # Only editable if in 'EN_PROCES' state
    if candidatura.estat != EstatCandidatura.EN_PROCES:
        return JsonResponse(
            {'error': 'No pots editar aquesta candidatura, ja no està en procés.'},
            status=400
        )

    carta_presentacio = request.POST.get('carta_presentacio', '').strip()
    cv_adjunt = request.FILES.get('cv_adjunt')
    altres_adjunts = request.FILES.get('altres_adjunts')

    # Validations
    if not carta_presentacio:
        errors['carta_presentacio'] = 'La carta de presentació és obligatòria.'
    elif len(carta_presentacio) < 50:
        errors['carta_presentacio'] = 'La carta ha de tenir almenys 50 caràcters.'
    elif len(carta_presentacio) > 2000:
        errors['carta_presentacio'] = 'La carta no pot superar els 2000 caràcters.'

    if cv_adjunt:
        # Check against Django's FILE_UPLOAD_MAX_MEMORY_SIZE if applicable or set a custom limit
        # Default FILE_UPLOAD_MAX_MEMORY_SIZE is 2.5MB. You set 5MB in original.
        # Ensure your Django settings accommodate larger files if needed.
        if cv_adjunt.size > 5 * 1024 * 1024:  # 5MB
            errors['cv_adjunt'] = 'El CV no pot superar els 5MB.'

        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
        if cv_adjunt.content_type not in allowed_types:
            errors['cv_adjunt'] = 'Format no vàlid. Només PDF, DOC o DOCX.'

    if altres_adjunts:
        if altres_adjunts.size > 10 * 1024 * 1024:  # 10MB
            errors['altres_adjunts'] = 'Els altres documents no poden superar els 10MB.'

    if errors:
        return JsonResponse({'errors': errors}, status=400) # Bad Request

    # If no errors, save
    try:
        candidatura.carta_presentacio = carta_presentacio
        
        if cv_adjunt:
            candidatura.cv_adjunt = cv_adjunt
        
        if altres_adjunts:
            candidatura.altres_adjunts = altres_adjunts
        
        candidatura.save()
        return JsonResponse({'message': 'Candidatura actualitzada correctament!'}, status=200) # OK
    except Exception as e:
        # Catch any unexpected errors during save
        return JsonResponse({'error': f'Hi ha hagut un error inesperat en desar la candidatura: {str(e)}'}, status=500) # Internal Server Error
