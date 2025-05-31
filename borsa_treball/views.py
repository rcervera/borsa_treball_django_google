from django.shortcuts import render

# Create your views here.

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .models import Noticia

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

