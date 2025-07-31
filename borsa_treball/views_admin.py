from django.shortcuts import render
from django.utils import timezone
from datetime import date
from django.db.models import Count, Avg
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from .models import Oferta, Estudiant, Empresa, Candidatura, EstatCandidatura

@login_required
@staff_member_required
def informe_curs_view(request):
    """
    Genera un informe d'activitat de la borsa de treball per a un període determinat,
    per defecte el curs acadèmic actual.
    """
    # 1. Determinar les dates per defecte (curs acadèmic actual)
    today = timezone.now().date()
    if today.month >= 9:
        default_start_date = date(today.year, 9, 1)
        default_end_date = date(today.year + 1, 8, 31)
    else:
        default_start_date = date(today.year - 1, 9, 1)
        default_end_date = date(today.year, 8, 31)

    # 2. Obtenir les dates de la petició GET o utilitzar les de per defecte
    start_date_str = request.GET.get('start_date', default_start_date.strftime('%Y-%m-%d'))
    end_date_str = request.GET.get('end_date', default_end_date.strftime('%Y-%m-%d'))

    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
    except (ValueError, TypeError):
        start_date = default_start_date
        end_date = default_end_date
        
    # 3. Realitzar les consultes a la base de dades
    
    # Ofertes creades en el període
    ofertes_period = Oferta.objects.filter(data_publicacio__range=[start_date, end_date])
    num_ofertes = ofertes_period.count()
    
    # Nous estudiants i empreses registrats
    # Filtrem per la data de registre de l'usuari associat
    num_alumnes_nous = Estudiant.objects.filter(usuari__data_registre__date__range=[start_date, end_date]).count()
    num_empreses_noves = Empresa.objects.filter(usuari__data_registre__date__range=[start_date, end_date]).count()
    
    # Candidatures i contractacions
    candidatures_period = Candidatura.objects.filter(data_candidatura__date__range=[start_date, end_date])
    num_candidatures = candidatures_period.count()
    
    # Filtrem per data_canvi_estat per saber quan es va marcar com a contractat
    num_contractats = Candidatura.objects.filter(
        estat=EstatCandidatura.CONTRATADA,
        data_canvi_estat__date__range=[start_date, end_date]
    ).count()

    # Mitjana de candidatures per oferta
    if num_ofertes > 0:
        mitjana_candidatures_per_oferta = round(num_candidatures / num_ofertes, 2)
    else:
        mitjana_candidatures_per_oferta = 0

    # 4. Càlculs addicionals per enriquir l'informe
    
    # Diccionari per mapejar codis a noms llegibles
    tipus_contracte_display = dict(Oferta.TIPUS_CONTRACTE)
    
    # Ofertes per tipus de contracte
    ofertes_per_tipus_contracte = list(ofertes_period
        .values('tipus_contracte')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    # Afegim el nom llegible
    for item in ofertes_per_tipus_contracte:
        item['nom_llegible'] = tipus_contracte_display.get(item['tipus_contracte'], 'Desconegut')

    # Top 5 empreses amb més ofertes
    top_empreses = list(ofertes_period
        .values('empresa__nom_comercial')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    
    # Ofertes per família professional (a través dels cicles)
    ofertes_per_familia = list(ofertes_period
        .filter(cicles__familia__nom__isnull=False)
        .values('cicles__familia__nom')
        .annotate(count=Count('id', distinct=True)) # 'distinct=True' per no comptar la mateixa oferta varies vegades si té cicles de la mateixa familia
        .order_by('-count')
    )

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'num_ofertes': num_ofertes,
        'num_alumnes_nous': num_alumnes_nous,
        'num_empreses_noves': num_empreses_noves,
        'num_candidatures': num_candidatures,
        'num_contractats': num_contractats,
        'mitjana_candidatures_per_oferta': mitjana_candidatures_per_oferta,
        'ofertes_per_tipus_contracte': ofertes_per_tipus_contracte,
        'top_empreses': top_empreses,
        'ofertes_per_familia': ofertes_per_familia,
    }

    return render(request, 'borsa_treball/informes/informe_curs.html', context)