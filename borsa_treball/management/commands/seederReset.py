from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import transaction
from borsa_treball.models import (
    Usuari, FamiliaProfessional, Cicle, Sector, CapacitatClau,
    Estudiant, EstudiEstudiant, Empresa, Oferta, Funcio, Candidatura,
    Noticia, RegistreAuditoria, NivellIdioma
)

class Command(BaseCommand):
    help = 'Inicialitza només dades base i un admin'

    def handle(self, *args, **options):
        self.stdout.write("Inicialitzant dades base i usuari admin...")

        try:
            with transaction.atomic():
                self.netejar_dades()
                self.crear_dades_base()
                self.crear_admin()
                self.stdout.write(self.style.SUCCESS("Seeder executat correctament."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error durant l'execució: {str(e)}"))

    def netejar_dades(self):
        """Elimina totes les dades en l'ordre correcte per evitar errors de FK"""
        self.stdout.write("Eliminant dades existents...")

        models_a_netejar = [
            Candidatura, Funcio, Oferta, EstudiEstudiant, Estudiant, Empresa,
            Usuari, CapacitatClau, Cicle, FamiliaProfessional, Sector,
            Noticia, RegistreAuditoria, NivellIdioma
        ]

        for model in models_a_netejar:
            count = model.objects.count()
            if count > 0:
                model.objects.all().delete()
                self.stdout.write(f"{count} registres eliminats de {model.__name__}")

    def crear_dades_base(self):
        """Crea famílies, cicles, sectors i capacitats"""
        self.stdout.write("Creant dades base...")

        # Famílies
        families = [
            {'codi': 'ADG', 'nom': 'Administració i Gestió'},
            {'codi': 'COM', 'nom': 'Comerç i Màrqueting'},
            {'codi': 'IFC', 'nom': 'Informàtica i Comunicacions'},          
            {'codi': 'SSC', 'nom': 'Serveis Socioculturals i a la Comunitat'},
        ]

        for f in families:
            FamiliaProfessional.objects.create(codi=f['codi'], nom=f['nom'])

        # Cicles (exemple abreujat — pots copiar els que necessitis de l'script original)
        cicles = [
            # Grau Mitjà (GM)
            {'codi': 'CFPM AG10', 'familia': 'ADG', 'nom': 'gestió administrativa', 'grau': 'GM', 'durada': 2000},
            {'codi': 'CFPM AG11', 'familia': 'ADG', 'nom': 'gestió administrativa (en l’àmbit jurídic)', 'grau': 'GM', 'durada': 2000},
            {'codi': 'CFPM CM10', 'familia': 'COM', 'nom': 'activitats comercials', 'grau': 'GM', 'durada': 2000},
            {'codi': 'CFPM SC10', 'familia': 'SSC', 'nom': 'atenció a persones en situació de dependència', 'grau': 'GM', 'durada': 2000},
            {'codi': 'CFPM IC10', 'familia': 'IFC', 'nom': 'sistemes microinformàtics i xarxes', 'grau': 'GM', 'durada': 2000},

            # Grau Superior (GS)
            {'codi': 'CFPS AGB0', 'familia': 'ADG', 'nom': 'administració i finances', 'grau': 'GS', 'durada': 2000},
            {'codi': 'CFPS AGA0', 'familia': 'ADG', 'nom': 'assistència a la direcció', 'grau': 'GS', 'durada': 2000},
            {'codi': 'CFPS CMA0', 'familia': 'COM', 'nom': 'gestió de vendes i espais comercials', 'grau': 'GS', 'durada': 2000},
            {'codi': 'CFPS CMD0', 'familia': 'COM', 'nom': 'màrqueting i publicitat', 'grau': 'GS', 'durada': 2000},
            {'codi': 'CFPS CMC0', 'familia': 'COM', 'nom': 'gestió del transport i logística', 'grau': 'GS', 'durada': 2000},
            {'codi': 'CFPS CMB0', 'familia': 'COM', 'nom': 'comerç internacional', 'grau': 'GS', 'durada': 2000},
            {'codi': 'CFPS SCB0', 'familia': 'SSC', 'nom': 'educació infantil', 'grau': 'GS', 'durada': 2000},
            {'codi': 'CFPS SCC0', 'familia': 'SSC', 'nom': 'integració social', 'grau': 'GS', 'durada': 2000},
            {'codi': 'CFPS SCA0', 'familia': 'SSC', 'nom': 'animació sociocultural i turística', 'grau': 'GS', 'durada': 2000},
            {'codi': 'CFPS ICA1', 'familia': 'IFC', 'nom': 'administració de sistemes informàtics en xarxa. perfil professional ciberseguretat', 'grau': 'GS', 'durada': 2000},
            {'codi': 'CFPS ICA0', 'familia': 'IFC', 'nom': 'administració de sistemes informàtics en xarxa', 'grau': 'GS', 'durada': 2000},
            {'codi': 'CFPS ICB0', 'familia': 'IFC', 'nom': 'desenvolupament d\'aplicacions multiplataforma', 'grau': 'GS', 'durada': 2000},
            {'codi': 'CFPS ICC0', 'familia': 'IFC', 'nom': 'desenvolupament d\'aplicacions web', 'grau': 'GS', 'durada': 2000},

            # Cursos d'Especialització
            {'codi': 'CEFP IC01', 'familia': 'IFC', 'nom': 'curs d\'especialització en ciberseguretat en tecnologies de la informació', 'grau': 'GS', 'durada': 600},
            {'codi': 'CEFP IC03', 'familia': 'IFC', 'nom': 'curs d\'especialització en intel·ligència artificial i big data', 'grau': 'GS', 'durada': 600},
        ]


        for c in cicles:
            familia = FamiliaProfessional.objects.get(codi=c['familia'])
            Cicle.objects.create(codi=c['codi'], nom=c['nom'], grau=c['grau'], durada=c['durada'], familia=familia)

        # Sectors
        sectors = [
            'Informàtica i Telecomunicacions', 'Comerç i Distribució',
            'Sanitat i Serveis Socials', 'Administració Pública',
            'Educació', 'Hostaleria i Turisme', 'Indústria',
            'Construcció', 'Serveis Financers', 'Altres'
        ]
        for nom in sectors:
            Sector.objects.create(nom=nom)

        # Capacitats Clau
        capacitats = [
            {'nom': 'Capacitat per comunicar-se', 'categoria': 'Professional'},
            {'nom': 'Iniciativa pròpia', 'categoria': 'Professional'},
            {'nom': 'Capacitat de treballar en equip i cooperació', 'categoria': 'Professional'},
            {'nom': 'Disponibilitat d\'aprenentatge', 'categoria': 'Professional'},
            {'nom': 'Disposició per a la responsabilitat', 'categoria': 'Professional'},
            {'nom': 'Productivitat i compromís', 'categoria': 'Professional'},
            {'nom': 'Empatia', 'categoria': 'Professional'},
            {'nom': 'Resolució de conflictes', 'categoria': 'Professional'},
            {'nom': 'Capacitat de lideratge', 'categoria': 'Professional'},
            {'nom': 'Treballar en un entorn internacional', 'categoria': 'Professional'},
        ]
        for c in capacitats:
            CapacitatClau.objects.create(nom=c['nom'], descripcio=f"Competència en {c['nom']}", categoria=c['categoria'])

    def crear_admin(self):
        """Crea l'usuari administrador"""
        Usuari.objects.create(
            email='rcerver4@xtec.cat',
            nom='Ramon',
            cognoms='Cervera Zaragoza',
            tipus='ADM',
            password=make_password('admin123'),
            is_staff=True,
            is_superuser=True,
            telefon='977212836',
        )
        self.stdout.write("Usuari admin creat: rcerver4@xtec.cat  / admin123")
