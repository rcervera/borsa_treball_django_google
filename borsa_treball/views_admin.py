# views.py (versió actualitzada)

from django.shortcuts import render
from django.utils import timezone
from datetime import date
from django.db.models import Count, Sum, Avg
from .models import Oferta, Estudiant, Empresa, Candidatura, EstatCandidatura
import json # Importem json per si calgués, encara que el tag 'json_script' ho gestiona internament
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

@login_required
@staff_member_required
def informe_curs_view(request):
    """
    Genera un informe d'activitat i una comparativa històrica dels últims 4 cursos.
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
    except ValueError:
        start_date = default_start_date
        end_date = default_end_date
        
    # --- Càlculs per a l'informe principal (període actual) ---
      
    ofertes_period = Oferta.objects.filter(data_publicacio__range=[start_date, end_date])
    num_ofertes = ofertes_period.count()   
    num_vacants = ofertes_period.aggregate(total=Sum('numero_vacants'))['total'] or 0
    num_alumnes_nous = Estudiant.objects.filter(usuari__data_registre__date__range=[start_date, end_date]).count()
    num_empreses_noves = Empresa.objects.filter(usuari__data_registre__date__range=[start_date, end_date]).count()
    num_candidatures = Candidatura.objects.filter(data_candidatura__date__range=[start_date, end_date]).count()
    num_contractats = Candidatura.objects.filter(
        estat=EstatCandidatura.CONTRATADA,
        data_canvi_estat__date__range=[start_date, end_date]
    ).count()

    # --- NOVES MITJANES DE VALORACIÓ D'EMPRESA ---
    valoracions = ofertes_period.aggregate(
        mitjana_qualitat=Avg('qualitat_candidats'),
        mitjana_gestio=Avg('gestio_proces')
    )

    mitjana_qualitat_candidats = round(valoracions['mitjana_qualitat'], 2) if valoracions['mitjana_qualitat'] else 0
    mitjana_gestio_proces = round(valoracions['mitjana_gestio'], 2) if valoracions['mitjana_gestio'] else 0
    
    if num_ofertes > 0:
        mitjana_candidatures_per_oferta = round(num_candidatures / num_ofertes, 2)
    else:
        mitjana_candidatures_per_oferta = 0

    tipus_contracte_display = dict(Oferta.TIPUS_CONTRACTE)
    ofertes_per_tipus_contracte = list(ofertes_period.values('tipus_contracte').annotate(count=Count('id')).order_by('-count'))
    for item in ofertes_per_tipus_contracte:
        item['nom_llegible'] = tipus_contracte_display.get(item['tipus_contracte'], 'Desconegut')
    top_empreses = list(ofertes_period.values('empresa__nom_comercial').annotate(count=Count('id')).order_by('-count')[:5])
    ofertes_per_familia = list(ofertes_period.filter(cicles__familia__nom__isnull=False).values('cicles__familia__nom').annotate(count=Count('id', distinct=True)).order_by('-count'))

    # --- NOU: Càlcul de dades per a la gràfica històrica ---
    
    chart_data = {
        'labels': [],
        'num_ofertes': [],
        'num_candidatures': [],
        'num_contractats': [],
        'mitjana_qualitat': [],      
        'mitjana_gestio': [],        
    }

    for i in range(4):  # Bucle per als últims 4 anys (0, 1, 2, 3)
        # Calculem les dates del període històric
        period_start = start_date.replace(year=start_date.year - i)
        period_end = end_date.replace(year=end_date.year - i)
        
        # Generem una etiqueta per al gràfic
        label = f"Curs {period_start.year % 100}/{period_end.year % 100}"
        
        # Realitzem les consultes per a aquest període
        p_ofertes = Oferta.objects.filter(data_publicacio__range=[period_start, period_end]).count()
        p_candidatures = Candidatura.objects.filter(data_candidatura__date__range=[period_start, period_end]).count()
        p_contractats = Candidatura.objects.filter(
            estat=EstatCandidatura.CONTRATADA,
            data_canvi_estat__date__range=[period_start, period_end]
        ).count()

        # Ofertes del període (només tancades millor)
        p_ofertes_qs = Oferta.objects.filter(
            data_publicacio__range=[period_start, period_end],
            estat='TC'  # recomanat!
        )

        valoracions = p_ofertes_qs.aggregate(
            mitjana_qualitat=Avg('qualitat_candidats'),
            mitjana_gestio=Avg('gestio_proces')
        )

        p_mitjana_qualitat = round(valoracions['mitjana_qualitat'], 2) if valoracions['mitjana_qualitat'] else 0
        p_mitjana_gestio = round(valoracions['mitjana_gestio'], 2) if valoracions['mitjana_gestio'] else 0
        
        # Afegim les dades a les llistes
        chart_data['labels'].append(label)
        chart_data['num_ofertes'].append(p_ofertes)
        chart_data['num_candidatures'].append(p_candidatures)
        chart_data['num_contractats'].append(p_contractats)
        chart_data['mitjana_qualitat'].append(p_mitjana_qualitat)
        chart_data['mitjana_gestio'].append(p_mitjana_gestio)

    # Invertim les llistes per tenir un ordre cronològic al gràfic (del més antic al més nou)
    for key in chart_data:
        chart_data[key].reverse()

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'num_ofertes': num_ofertes,
        'num_vacants': num_vacants,
        'num_alumnes_nous': num_alumnes_nous,
        'num_empreses_noves': num_empreses_noves,
        'num_candidatures': num_candidatures,
        'num_contractats': num_contractats,
        'mitjana_candidatures_per_oferta': mitjana_candidatures_per_oferta,
        'ofertes_per_tipus_contracte': ofertes_per_tipus_contracte,
        'top_empreses': top_empreses,
        'ofertes_per_familia': ofertes_per_familia,
        'chart_data': chart_data,  # Afegim les dades del gràfic al context
        'mitjana_qualitat_candidats': mitjana_qualitat_candidats,
        'mitjana_gestio_proces': mitjana_gestio_proces,
    }

    return render(request, 'borsa_treball/informes/informe_curs.html', context)
