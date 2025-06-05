from django.shortcuts import render

# Create your views here.

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .models import Empresa, Noticia, Sector, Usuari
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
import re

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

        else:
            # Si és un altre tipus autenticat (ex: admin)
            context['noticies'] = noticies

    else:
        # Usuari no autenticat: només notícies per a tothom
        context['noticies'] = noticies.filter(destinatari='TOTHOM')

    return render(request, 'index.html', context)

#
#  REGISTRE EMPRESA
#
def registre_empresa(request):
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
