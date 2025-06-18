from django.shortcuts import render

# Create your views here.

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .models import Cicle, Empresa, Estudiant, Noticia, Sector, Usuari, Oferta, Candidatura
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
import re
from django.core.paginator import Paginator
from django.utils import timezone

#
#  LOGIN
#
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('index')  
        else:
            messages.error(request, 'Correu electrònic o contrasenya incorrectes.')

    return render(request, 'login.html')


#
#  INDEX
#
def index(request):

    if not request.user.is_authenticated:
        return render(request, 'landing.html')
    
    user = request.user
    context = {}

    noticies = Noticia.objects.filter(visible=True)

    if user.is_authenticated:
        context['user_type'] = user.get_tipus_display()

        if user.tipus == 'EST':
            try:
                context['estudiant'] = user.estudiant
                context['cicle'] = user.estudiant.cicle
            except:
                pass
            # Notícies per a estudiants i tothom
            context['noticies'] = noticies.filter(destinatari__in=['TOTHOM', 'ESTUDIANTS'])

        elif user.tipus == 'EMP':
            try:
                context['empresa'] = user.empresa
            except:
                pass
            # Notícies per a empreses i tothom
            context['noticies'] = noticies.filter(destinatari__in=['TOTHOM', 'EMPRESES'])

        elif user.tipus == 'ADM' or user.tipus == 'RESPONSABLE':
            # Si és un altre tipus autenticat (ex: admin)
            context['noticies'] = noticies
            # Fetch unreviewed audit logs for admin
            registres_auditoria_queryset = RegistreAuditoria.objects.filter(
                revisat=False
            ).order_by('-data') # Order by data, newest first

             # --- Global Statistics ---
            today = timezone.now().date() # Get today's date for filtering active offers

            # Total Users (assuming 'Usuari' model represents all users including students/companies etc.)
            context['total_usuaris'] = Usuari.objects.count() 
            
            # Total Companies
            context['total_empreses'] = Empresa.objects.count()

            # Total Active Offers (visible, active, AND NOT EXPIRED)
            active_offers_queryset = Oferta.objects.filter(
                visible=True,
                activa=True,
                data_limit__gte=today # This is the crucial change for the index view stats
            )
            context['total_ofertes_actives'] = active_offers_queryset.count()

            # Total Candidatures for Active Offers (only for those not expired)
            context['total_candidatures_actives'] = Candidatura.objects.filter(
                oferta__in=active_offers_queryset 
            ).count()


            paginator = Paginator(registres_auditoria_queryset, 10) # 10 records per page
            page_number = request.GET.get('page') # Get the page number from the request
            page_obj = paginator.get_page(page_number) # Get the Page object

            context['registres_auditoria'] = page_obj # Add the paginated audit logs to context


    else:
        # Usuari no autenticat: només notícies per a tothom
        context['noticies'] = noticies.filter(destinatari='TOTHOM')

    context['current_page'] = 'inici'
    return render(request, 'index.html', context)

#
#  REGISTRE EMPRESA
#
def registre_empresa_antiga(request):
    # Obtenir tots els sectors per al dropdown
    sectors = Sector.objects.all()
    
    if request.method == 'POST':
        # Obtenir dades del formulari       
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        nom = request.POST.get('nom', '').strip()
        cognoms = request.POST.get('cognoms', '').strip()
        cif = request.POST.get('cif', '').strip().upper()
        nom_comercial = request.POST.get('nom_comercial', '').strip()
        rao_social = request.POST.get('rao_social', '').strip()
        sector_id = request.POST.get('sector')
        telefon = request.POST.get('telefon', '').strip()
        
        # Diccionari per guardar errors
        errors = {}
        
        # Validacions bàsiques
        
        if not email:
            errors['email'] = ['El correu electrònic és obligatori.']
        elif Usuari.objects.filter(email=email).exists():
            errors['email'] = ['Aquest correu electrònic ja està registrat.']
            
        if not password1:
            errors['password1'] = ['La contrasenya és obligatòria.']
        else:
            # Validar contrasenya amb els validadors de Django
            try:
                validate_password(password1)
            except ValidationError as e:
                errors['password1'] = list(e.messages)
                
        if not password2:
            errors['password2'] = ['Has de confirmar la contrasenya.']
        elif password1 != password2:
            errors['password2'] = ['Les contrasenyes no coincideixen.']
            
        if not nom:
            errors['nom'] = ['El nom és obligatori.']
        if not cognoms:
            errors['cognoms'] = ['Els cognoms són obligatoris.']

        # Validacions específiques d'empresa
        if not cif:
            errors['cif'] = ['El CIF/NIF és obligatori.']
        else:
            # Validar format CIF/NIF
            cif_pattern = r'^[A-Z][0-9]{8}$|^[0-9]{8}[A-Z]$'
            if not re.match(cif_pattern, cif):
                errors['cif'] = ['Format de CIF/NIF no vàlid. Utilitza: A12345678 o 12345678A']
            elif Empresa.objects.filter(cif=cif).exists():
                errors['cif'] = ['Aquest CIF/NIF ja està registrat.']
                
        if not nom_comercial:
            errors['nom_comercial'] = ['El nom comercial és obligatori.']
        elif len(nom_comercial) < 2:
            errors['nom_comercial'] = ['El nom comercial ha de tenir almenys 2 caràcters.']
            
        if not rao_social:
            errors['rao_social'] = ['La raó social és obligatòria.']
        elif len(rao_social) < 2:
            errors['rao_social'] = ['La raó social ha de tenir almenys 2 caràcters.']
            
        if not sector_id:
            errors['sector'] = ['Has de seleccionar un sector.']
        else:
            try:
                sector = Sector.objects.get(id=sector_id)
            except Sector.DoesNotExist:
                errors['sector'] = ['El sector seleccionat no és vàlid.']

        if not telefon:
            errors['telefon'] = ['El telèfon és obligatori.']        
          
        
        # Si no hi ha errors, crear l'usuari i empresa
        if not errors:
            try:
                with transaction.atomic():
                    # Crear usuari
                    user = Usuari.objects.create_user(                       
                        email=email,
                        password=password1,
                        tipus='EMP',
                        nom=nom,
                        cognoms=cognoms
                    )
                    
                    # Crear perfil d'empresa
                    empresa = Empresa.objects.create(
                        usuari=user,
                        cif=cif,
                        nom_comercial=nom_comercial,
                        rao_social=rao_social,
                        sector=sector,
                        telefon=telefon
                    )
                    
                    # Autenticar i fer login
                    user = authenticate(email=email, password=password1)
                    if user:
                        login(request, user)
                        messages.success(request, f'Benvinguda {nom_comercial}! El compte de la vostra empresa s\'ha creat correctament.')
                        return redirect('index')
                    else:
                        messages.error(request, 'Error en l\'autenticació. Si us plau, inicia sessió manualment.')
                        return redirect('login')
                        
            except Exception as e:
                messages.error(request, 'Hi ha hagut un error en crear el compte. Si us plau, torna-ho a intentar.')
                errors['general'] = [str(e)]
        
        # Si hi ha errors, tornar al formulari amb els errors i dades
        context = {
            'sectors': sectors,
            'errors': errors,
            'form_data': {
                'telefon': telefon,
                'email': email,
                'cif': cif,
                'nom_comercial': nom_comercial,
                'rao_social': rao_social,
                'sector': sector_id,
                'nom': nom,
                'cognoms': cognoms
            }
        }
        return render(request, 'registre_empresa.html', context)
    
    # GET request - mostrar formulari buit
    context = {
        'sectors': sectors,
        'errors': {},
        'form_data': {}
    }
    return render(request, 'borsa_treball/registre_empresa.html', context)


# borsa_treball/views.py

from django.shortcuts import render
from django.http import JsonResponse # Importa JsonResponse
from django.db import transaction # Importa transaction per a operacions atòmiques
from django.contrib.auth import authenticate, login
from django.contrib.auth.password_validation import validate_password # Importa el validador de contrasenyes
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST # Per assegurar-nos que només accepta POST
import re
import json # Per carregar dades JSON de la petició

# Importa els teus models
from .models import Usuari, Empresa, Sector, RegistreAuditoria # Assegura't que tots els models estiguin importats




@require_POST
def registre_empresa(request):
    """
    API endpoint per al registre d'una nova empresa i el seu usuari associat.
    Retorna una resposta JSON.
    """
    # Intentar carregar el cos de la petició com a JSON
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Dades de petició no vàlides (JSON mal format).'}, status=400)

    # Obtenir dades del JSON de la petició
    email = data.get('email', '').strip()
    password1 = data.get('password1', '')
    password2 = data.get('password2', '')
    nom = data.get('nom', '').strip()
    cognoms = data.get('cognoms', '').strip()
    cif = data.get('cif', '').strip().upper()
    nom_comercial = data.get('nom_comercial', '').strip()
    rao_social = data.get('rao_social', '').strip()
    sector_id = data.get('sector')
    telefon = data.get('telefon', '').strip()
    terms = data.get('terms', '').strip()

    # Diccionari per guardar errors
    errors = {}

    # Validacions bàsiques (reutilitzant la teva lògica)

    if not terms:
        errors['terms'] = ['Has d\'acceptar els termes i condicions']

    if not email:
        errors['email'] = ['El correu electrònic és obligatori.']
    elif Usuari.objects.filter(email=email).exists():
        errors['email'] = ['Aquest correu electrònic ja està registrat.']
        
    if not password1:
        errors['password1'] = ['La contrasenya és obligatòria.']
    else:
        # Validar contrasenya amb els validadors de Django
        try:
            validate_password(password1)
        except ValidationError as e:
            errors['password1'] = list(e.messages)
            
    if not password2:
        errors['password2'] = ['Has de confirmar la contrasenya.']
    elif password1 != password2:
        errors['password2'] = ['Les contrasenyes no coincideixen.']
        
    if not nom:
        errors['nom'] = ['El nom és obligatori.']
    if not cognoms:
        errors['cognoms'] = ['Els cognoms són obligatoris.']

    # Validacions específiques d'empresa
    if not cif:
        errors['cif'] = ['El CIF/NIF és obligatori.']
    else:
        # Validar format CIF/NIF
        cif_pattern = r'^[A-Z][0-9]{8}$|^[0-9]{8}[A-Z]$'
        if not re.match(cif_pattern, cif):
            errors['cif'] = ['Format de CIF/NIF no vàlid. Utilitza: A12345678 o 12345678A']
        elif Empresa.objects.filter(cif=cif).exists():
            errors['cif'] = ['Aquest CIF/NIF ja està registrat.']
            
    if not nom_comercial:
        errors['nom_comercial'] = ['El nom comercial és obligatori.']
    elif len(nom_comercial) < 2:
        errors['nom_comercial'] = ['El nom comercial ha de tenir almenys 2 caràcters.']
        
    if not rao_social:
        errors['rao_social'] = ['La raó social és obligatòria.']
    elif len(rao_social) < 2:
        errors['rao_social'] = ['La raó social ha de tenir almenys 2 caràcters.']
        
    sector = None
    if not sector_id:
        errors['sector'] = ['Has de seleccionar un sector.']
    else:
        try:
            sector = Sector.objects.get(id=sector_id)
        except Sector.DoesNotExist:
            errors['sector'] = ['El sector seleccionat no és vàlid.']

    if not telefon:
        errors['telefon'] = ['El telèfon és obligatori.']
        
    # Si hi ha errors, retornar JsonResponse amb errors
    if errors:
        return JsonResponse({'success': False, 'errors': errors}, status=400) # 400 Bad Request

    # Si no hi ha errors, intentar crear l'usuari i empresa
    try:
        with transaction.atomic(): # Assegura que la creació d'usuari i empresa és atòmica
            # Crear usuari
            user = Usuari.objects.create_user(
                email=email,
                password=password1,
                tipus='EMP', # Assegura que el tipus d'usuari és Empresa
                nom=nom,
                cognoms=cognoms
            )
            
            # Crear perfil d'empresa
            empresa = Empresa.objects.create(
                usuari=user,
                cif=cif,
                nom_comercial=nom_comercial,
                rao_social=rao_social,
                sector=sector,
                telefon=telefon
            )
            
            print(empresa.usuari.id)

            # Registrar al log d'auditoria (opcional, si el teu model ho permet)
            RegistreAuditoria.objects.create(
                accio="Alta Empresa",
                model_afectat="Empresa",
                #objecte_id=empresa.id,
                descripcio=f"Nova empresa registrada: {nom_comercial} ({cif})",
                usuari=user # L'usuari que s'acaba de crear
            )

            # L'autenticació i login es faran al client si el registre és exitós.
            # En una API, NO autentiquem l'usuari directament al backend després d'un registre reeixit
            # si l'objectiu és una aplicació SPA o que el client gestioni la sessió.
            # Normalment es retornaria un token JWT o es donarien instruccions per fer login.
            # Per simplicitat amb la teva estructura actual de Django, podríem retornar un missatge d'èxit.
            
            return JsonResponse({
                'success': True,
                'message': f'Benvinguda {nom_comercial}! El compte de la vostra empresa s\'ha creat correctament. Ara pots iniciar sessió.'
            }, status=201) # 201 Created

    except Exception as e:
        # Registrar l'excepció per a debugging
        print(e)
        return JsonResponse({
            'success': False,
            'message': 'Hi ha hagut un error intern en crear el compte. Si us plau, torna-ho a intentar.',
            'errors': {'general': [str(e)]} # Error general
        }, status=500) # 500 Internal Server Error



# Per a peticions GET, simplement mostrem el formulari (sense canvis)
def mostrar_registre_empresa(request):
    sectors = Sector.objects.all()
    context = {
        'sectors': sectors,
        'errors': {}, # Buit per a la primera càrrega
        'form_data': {} # Buit per a la primera càrrega
    }
    return render(request, 'borsa_treball/registre_empresa.html', context)


def mostrar_registre_estudiant(request):
    cicles = Cicle.objects.all()
    context = {
        'cicles': cicles,
        'errors': {}, # Buit per a la primera càrrega
        'form_data': {} # Buit per a la primera càrrega
    }
    return render(request, 'borsa_treball/registre_estudiant.html', context)


import json
import re
from datetime import datetime
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone 

# Importa tots els models que necessites
from .models import Usuari, Estudiant, Cicle, EstudiEstudiant, RegistreAuditoria 

@require_POST
def registre_estudiant(request):
    """
    API endpoint per al registre d'un nou estudiant i el seu usuari associat.
    Retorna una resposta JSON.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Dades de petició no vàlides (JSON mal format).'}, status=400)

    # Obtenir dades del JSON de la petició
    email = data.get('email', '').strip()
    password1 = data.get('password1', '')
    password2 = data.get('password2', '')
    nom = data.get('nom', '').strip()
    cognoms = data.get('cognoms', '').strip()
    dni = data.get('dni', '').strip()
    telefon = data.get('telefon', '').strip()
    
    cicle_id_str = data.get('cicle', '').strip() # Ara esperem l'ID com a cadena
    any_inici_str = data.get('any_inici', '').strip()
    any_fi_str = data.get('any_fi', '').strip()
    
    terms = data.get('terms', '')

    errors = {}

    # Validacions bàsiques
    if not terms:
        errors['terms'] = ['Has d\'acceptar els termes i condicions.']

    if not email:
        errors['email'] = ['El correu electrònic és obligatori.']
    elif Usuari.objects.filter(email=email).exists():
        errors['email'] = ['Aquest correu electrònic ja està registrat.']
        
    if not password1:
        errors['password1'] = ['La contrasenya és obligatòria.']
    else:
        try:
            validate_password(password1)
        except ValidationError as e:
            errors['password1'] = list(e.messages)
            
    if not password2:
        errors['password2'] = ['Has de confirmar la contrasenya.']
    elif password1 != password2:
        errors['password2'] = ['Les contrasenyes no coincideixen.']
        
    if not nom:
        errors['nom'] = ['El nom és obligatori.']
    if not cognoms:
        errors['cognoms'] = ['Els cognoms són obligatoris.']

    # Validacions específiques d'estudiant
    if not dni:
        errors['dni'] = ['El DNI és obligatori.']
    else:
        dni_pattern = r'^\d{8}[A-Z]$' 
        if not re.match(dni_pattern, dni):
            errors['dni'] = ['Format de DNI no vàlid. Ha de ser 8 dígits seguits d\'una lletra (ex: 12345678A).']
        elif Estudiant.objects.filter(dni=dni).exists():
            errors['dni'] = ['Aquest DNI ja està registrat.']
            
    if not telefon:
        errors['telefon'] = ['El telèfon és obligatori.']
            
    # Validació i cerca de Cicle per ID
    cicle_obj = None
    if not cicle_id_str:
        errors['cicle'] = ['Els estudis actuals o darrers són obligatoris.']
    else:
        try:
            cicle_id = int(cicle_id_str)
            cicle_obj = Cicle.objects.get(id=cicle_id)
        except ValueError:
            errors['cicle'] = ['L\'ID del cicle ha de ser un número sencer vàlid.']
        except Cicle.DoesNotExist:
            errors['cicle'] = ['Els estudis seleccionats no existeixen.']
        
    if not any_inici_str:
        errors['any_inici'] = ['L\'any d\'inici dels estudis és obligatori.']
    
    # --- Validacions any_inici i any_fi ---
    any_inici = None
    any_fi = None
    
    if any_inici_str:
        try:
            any_inici = int(any_inici_str)
        except ValueError:
            errors['any_inici'] = ['L\'any d\'inici ha de ser un número sencer vàlid.']
        else:
            if any_inici > datetime.now().year:
                errors['any_inici'] = ['L\'any d\'inici no pot ser futur.']
            elif any_inici < 1900: # O un any mínim raonable per evitar errors extrems
                errors['any_inici'] = ['L\'any d\'inici és massa antic.']

    if any_fi_str:
        try:
            any_fi = int(any_fi_str)
        except ValueError:
            errors['any_fi'] = ['L\'any de finalització ha de ser un número sencer vàlid.']
        
    if any_inici is not None and any_fi is not None:
        # Aquesta validació només es fa si ambdós anys són números vàlids
        if any_fi <= any_inici:
            errors['any_fi'] = ['L\'any de finalització ha de ser posterior a l\'any d\'inici.']
    # --- Fi Validacions any_inici i any_fi ---

    # Si hi ha errors acumulats, retornar JsonResponse amb errors
    if errors:
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    # Si no hi ha errors i el cicle s'ha trobat, intentar crear l'usuari i estudiant
    try:
        with transaction.atomic(): # Assegura que la creació d'usuari i estudiant és atòmica
            # Crear usuari
            user = Usuari.objects.create_user(
                email=email,
                password=password1,
                tipus='EST', # Assegura que el tipus d'usuari és Estudiant
                nom=nom,
                cognoms=cognoms,
                telefon=telefon 
            )
            
            # Crear estudiant
            estudiant = Estudiant.objects.create(
                usuari=user,
                dni=dni             
            )

            # Crear EstudiEstudiant només si cicle_obj existeix i any_inici és vàlid
            # En aquest punt, cicle_obj i any_inici ja haurien d'estar validats si no hi ha errors.
            EstudiEstudiant.objects.create(
                estudiant=estudiant,
                cicle=cicle_obj, # Utilitzem l'objecte Cicle trobat
                any_inici=any_inici,
                any_fi=any_fi # any_fi pot ser None, la qual cosa és permesa pel model
            )

            # Registrar al log d'auditoria
            RegistreAuditoria.objects.create(
                accio="Alta Estudiant",
                model_afectat="Estudiant",
                # objecte_id=estudiant.id, # Pots descomentar si el camp objecte_id és obligatori o útil
                descripcio=f"Nou estudiant registrat: {nom} {cognoms} amb DNI {dni}. Estudis: {cicle_obj.nom} ({any_inici}-{any_fi or 'Actual'})",
                usuari=user # L'usuari que s'acaba de crear
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Benvinguda {nom}! El compte com estudiant s\'ha creat correctament. Ara pots iniciar sessió.'
            }, status=201) # 201 Created

    except Exception as e:
        # Registrar l'excepció per a debugging
        print(f"Error durant el registre de l'estudiant: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Hi ha hagut un error intern en crear el compte. Si us plau, torna-ho a intentar.',
            'errors': {'general': [f'Error intern: {e}']} 
        }, status=500) # 500 Internal Server Error