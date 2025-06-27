from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import transaction
from faker import Faker
import random
from datetime import datetime, timedelta, date
from django.utils.timezone import now
from borsa_treball.models import (
    CapacitatOferta, Usuari, FamiliaProfessional, Cicle, Sector, CapacitatClau, 
    Estudiant, EstudiEstudiant, Empresa, Oferta, 
    Funcio, Candidatura, Noticia, RegistreAuditoria,NivellIdioma
)

fake = Faker('es_ES')

class Command(BaseCommand):
    help = 'Crea dades completes: usuaris, empreses, estudiants, ofertes i candidatures'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Elimina totes les dades abans de crear-ne de noves',
        )
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='No demana confirmació per eliminar dades',
        )

    def handle(self, *args, **options):
        self.stdout.write("Iniciant creació de dades...")
        
        # Opció per netejar dades
        if options['clean']:
            if options['no_input'] or self.confirmar_neteja():
                self.netejar_dades()
        
        try:
            with transaction.atomic():
                # 1. Crear dades base
                self.crear_dades_base()
                
                # 2. Crear usuaris i perfils
                admin = self.crear_admin()
                empreses = self.crear_empreses()
                estudiants = self.crear_estudiants()
                
                # 3. Crear ofertes
                ofertes = self.crear_ofertes(empreses)
                
                # 4. Crear candidatures
                self.crear_candidatures(estudiants, ofertes)
                
                # 5. Crear notícies
                self.crear_noticies()
                
                self.stdout.write(self.style.SUCCESS("Totes les dades creades correctament!"))
                self.mostrar_resum()
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error creant dades: {str(e)}")
            )
            self.stdout.write("Prova executar amb --clean per eliminar dades existents")

    def confirmar_neteja(self):
        """Demana confirmació per eliminar dades"""
        resposta = input(
            "Això eliminarà TOTES les dades existents. "
            "Estàs segur? (escriu 'sí' per confirmar): "
        )
        return resposta.lower() in ['sí', 'si', 'yes', 'y']

    def netejar_dades(self):
        """Elimina totes les dades en l'ordre correcte per evitar errors de FK"""
        self.stdout.write("Eliminant dades existents...")
        
        # Ordre important per evitar errors de foreign key
        models_a_netejar = [
            Candidatura,
            Funcio,
            Oferta,
            EstudiEstudiant,
            Estudiant,
            Empresa,
            Usuari,  # Eliminar usuaris després dels perfils
            CapacitatClau,
            Cicle,
            FamiliaProfessional,
            Sector,
            Noticia,
            RegistreAuditoria,
        ]
        
        for model in models_a_netejar:
            count = model.objects.count()
            if count > 0:
                model.objects.all().delete()
                self.stdout.write(f"Eliminats {count} registres de {model.__name__}")
        
        self.stdout.write(self.style.SUCCESS("Dades eliminades correctament"))

    def crear_dades_base(self):
        """Crea families, cicles, sectors i capacitats"""
        self.stdout.write("Creant dades base...")
        
        # Families Professionals
        families = [
            {'codi': 'ADG', 'nom': 'Administració i Gestió'},
            {'codi': 'COM', 'nom': 'Comerç i Màrqueting'},
            {'codi': 'IFC', 'nom': 'Informàtica i Comunicacions'},          
            {'codi': 'SSC', 'nom': 'Serveis Socioculturals i a la Comunitat'},
        ]

        for familia in families:
            fp, created = FamiliaProfessional.objects.get_or_create(
                codi=familia['codi'],
                defaults={'nom': familia['nom']}
            )
            if created:
                self.stdout.write(f"Familia creada: {fp.nom}")

        # Cicles Formatius
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


        for cicle in cicles:
            familia = FamiliaProfessional.objects.get(codi=cicle['familia'])
            c, created = Cicle.objects.get_or_create(
                codi=cicle['codi'],
                defaults={
                    'familia': familia,
                    'nom': cicle['nom'],
                    'grau': cicle['grau'],
                    'durada': cicle['durada']
                }
            )
            if created:
                self.stdout.write(f"Cicle creat: {c.nom}")

        # Sectors
        sectors = [
            'Informàtica i Telecomunicacions', 'Comerç i Distribució',
            'Sanitat i Serveis Socials', 'Administració Pública',
            'Educació', 'Hostaleria i Turisme', 'Indústria',
            'Construcció', 'Serveis Financers', 'Altres'
        ]

        for sector in sectors:
            s, created = Sector.objects.get_or_create(nom=sector)
            if created:
                self.stdout.write(f"Sector creat: {s.nom}")

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

        for capacitat in capacitats:
            cc, created = CapacitatClau.objects.get_or_create(
                nom=capacitat['nom'],
                defaults={
                    'descripcio': f"Competència en {capacitat['nom']}",
                    'categoria': capacitat['categoria']
                }
            )
            if created:
                self.stdout.write(f"Capacitat creada: {cc.nom}")

    def crear_admin(self):
        """Crea l'usuari administrador"""
        admin, created = Usuari.objects.get_or_create(
            email='rcerver4@xtec.cat',
            defaults={
                'nom': 'Admin',
                'cognoms': 'Sistema',
                'tipus': 'ADM',
                'password': make_password('admin123'),
                'is_staff': True,
                'is_superuser': True,
                'telefon': '977123456',
            }
        )
        if created:
            self.stdout.write(f"Admin creat: {admin.email}")
        return admin

    def crear_empreses(self):
        """Crea 5 empreses amb usuaris"""
        self.stdout.write("Creant empreses...")
        empreses = []
        sectors = list(Sector.objects.all())
        
        noms_empreses = [
            'TechSolutions BCN', 'Comercial Mediterrani', 
            'Serveis Socials Tarragona', 'Consultoria Administrativa',
            'Innovació Digital'
        ]

        for i in range(5):
            email = f'empresa{i+1}@empresa.com'
            
            # Crear usuari empresa
            usuari, created = Usuari.objects.get_or_create(
                email=email,
                defaults={
                    'nom': fake.first_name(),
                    'cognoms': fake.last_name(),
                    'tipus': 'EMP',
                    'password': make_password('empresa123'),
                    'telefon': fake.phone_number()[:15],
                    'adreca': fake.address(),
                }
            )

            # Crear empresa si no existeix
            if created or not hasattr(usuari, 'empresa'):
                # Generar CIF únic
                cif_base = f'B{fake.random_number(digits=8)}'
                while Empresa.objects.filter(cif=cif_base).exists():
                    cif_base = f'B{fake.random_number(digits=8)}'

                empresa, emp_created = Empresa.objects.get_or_create(
                    usuari=usuari,
                    defaults={
                        'cif': cif_base,
                        'nom_comercial': noms_empreses[i],
                        'rao_social': f'{noms_empreses[i]} S.L.',
                        'sector': random.choice(sectors),
                        'descripcio': fake.text(max_nb_chars=300),
                        'num_treballadors': random.randint(10, 500),
                        'web': f'https://www.{fake.domain_name()}',
                        'telefon': fake.phone_number()[:15],
                    }
                )
            else:
                empresa = usuari.empresa
            
            empreses.append(empresa)
            self.stdout.write(f"Empresa: {empresa.nom_comercial}")

        return empreses

    def crear_estudiants(self):
        """Crea 10 estudiants amb estudis"""
        self.stdout.write("Creant estudiants...")
        estudiants = []
        cicles = list(Cicle.objects.all())
        centres = [
            'Institut Vidal i Barraquer', 'IES Tarragona',
            'Centre FP Mediterrani', 'Institut Tecnològic',
            'Centre d\'Estudis Professionals'
        ]

        for i in range(10):
            email = f'estudiant{i+1}@estudiant.com'

            # Generar DNI únic
            dni_base = f'{fake.random_number(digits=8)}B'
            while Estudiant.objects.filter(dni=dni_base).exists():
                dni_base = f'{fake.random_number(digits=8)}B'
            
            # Crear usuari estudiant
            usuari, created = Usuari.objects.get_or_create(
                email=email,
                defaults={                    
                    'nom': fake.first_name(),
                    'cognoms': fake.last_name(),
                    'tipus': 'EST',
                    'password': make_password('estudiant123'),
                    'telefon': fake.phone_number()[:15],
                    'data_naixement': fake.date_of_birth(minimum_age=18, maximum_age=25),
                    'adreca': fake.address(),
                }
            )

            # Crear estudiant si no existeix
            if created or not hasattr(usuari, 'estudiant'):
                estudiant, est_created = Estudiant.objects.get_or_create(
                    usuari=usuari,
                    dni = dni_base,
                )
            else:
                estudiant = usuari.estudiant

            # Crear estudis només si no en té
            if not estudiant.estudis.exists():
                num_estudis = random.randint(1, 3)
                any_actual = datetime.now().year
                
                for j in range(num_estudis):
                    cicle = random.choice(cicles)
                    any_inici = random.randint(any_actual - 5, any_actual - 1)
                    
                    # Evitar duplicats
                    if EstudiEstudiant.objects.filter(
                        estudiant=estudiant, 
                        cicle=cicle, 
                        any_inici=any_inici
                    ).exists():
                        continue
                    
                    # Determinar any_fi
                    any_fi = any_inici + 2 if random.choice([True, False]) else None

                    EstudiEstudiant.objects.create(
                        estudiant=estudiant,
                        cicle=cicle,
                        any_inici=any_inici,
                        any_fi=any_fi,
                        centre_estudis=random.choice(centres),
                    )

            estudiants.append(estudiant)
            self.stdout.write(f"Estudiant: {estudiant.usuari.get_full_name()}")

        return estudiants

    def crear_ofertes(self, empreses):
        """Crea 5 ofertes per cada empresa"""
        self.stdout.write("Creant ofertes...")
        ofertes = []
        cicles = list(Cicle.objects.all())
        capacitats = list(CapacitatClau.objects.all())
        
        titols_ofertes = [
            'Desenvolupador/a Junior', 'Tècnic/a Administratiu/va',
            'Especialista en Màrqueting', 'Tècnic/a de Sistemes',
            'Auxiliar Administratiu/va', 'Programador/a Web',
            'Responsable de Vendes', 'Tècnic/a de Suport',
            'Analista de Dades', 'Coordinador/a de Projectes'
        ]

        for empresa in empreses:
            # Eliminar ofertes existents d'aquesta empresa
            Oferta.objects.filter(empresa=empresa).delete()
            
            for i in range(5):
                data_limit = fake.date_between(start_date='+1w', end_date='+3M')
                
                oferta = Oferta.objects.create(
                    empresa=empresa,
                    titol=f"{random.choice(titols_ofertes)} - {empresa.nom_comercial}",
                    descripcio=fake.text(max_nb_chars=500),
                    data_publicacio=date.today(),
                    data_limit=data_limit,
                    tipus_contracte=random.choice(['PR', 'TC', 'TI', 'IN']),
                    jornada=random.choice(['CO', 'PA', 'FL']),
                    horari=random.choice([
                        'De 9:00 a 17:00', 'De 8:00 a 16:00',
                        'Horari flexible', 'Torn de matí'
                    ]),
                    salari=f'{random.randint(800, 2500)}€/mes',
                    requisits=fake.text(max_nb_chars=200),
                    lloc_treball=fake.city(),
                    contacte_nom=fake.name(),
                    contacte_email=fake.email(),
                    contacte_telefon=fake.phone_number()[:15],
                    estat=random.choice(['OC','RV','AC'])
                )

                # Assignar cicles i capacitats
                cicles_oferta = random.sample(cicles, random.randint(1, 3))
                oferta.cicles.set(cicles_oferta)

                capacitats_oferta = random.sample(capacitats, random.randint(2, 5))
                oferta.capacitats_clau.set(capacitats_oferta)

                capacitats_lliures_posibles = [  # 🆕 Capacitats text lliure
                    'Adaptabilitat', 'Treball en equip', 'Iniciativa',
                    'Comunicació eficaç', 'Pensament crític', 'Autonomia',
                    'Resolució de problemes', 'Creativitat', 'Responsabilitat',
                    'Atenció al detall'
                ]

                 # 🆕 Capacitats lliures
                capacitats_text = random.sample(capacitats_lliures_posibles, random.randint(1, 3))
                for nom in capacitats_text:
                    CapacitatOferta.objects.create(oferta=oferta, nom=nom)

                # Crear funcions
                funcions_text = [
                    'Desenvolupar aplicacions web amb tecnologies modernes',
                    'Gestionar la documentació administrativa',
                    'Donar suport tècnic als usuaris',
                    'Participar en reunions d\'equip',
                    'Mantenir actualitzada la base de dades',
                    'Elaborar informes periòdics',
                    'Coordinar amb altres departaments',
                    'Implementar millores en els processos'
                ]
                
                num_funcions = random.randint(2, 4)
                for j in range(num_funcions):
                    Funcio.objects.create(
                        oferta=oferta,
                        descripcio=random.choice(funcions_text),
                        ordre=j + 1
                    )

                # Afegir idiomes amb nivell
                NivellIdioma.objects.create(oferta=oferta, idioma="Català", nivell="nadiu")
                NivellIdioma.objects.create(oferta=oferta, idioma="Castellà", nivell="nadiu")
                NivellIdioma.objects.create(oferta=oferta, idioma="Anglès", nivell="parlat")

                ofertes.append(oferta)

            self.stdout.write(f"5 ofertes per {empresa.nom_comercial}")

        return ofertes

    def crear_candidatures(self, estudiants, ofertes):
        """Crea candidatures entre estudiants i ofertes"""
        self.stdout.write("Creant candidatures...")
        candidatures_creades = 0
        
        for estudiant in estudiants:
            # Eliminar candidatures existents
            Candidatura.objects.filter(estudiant=estudiant).delete()
            
            cicles_estudiant = [estudi.cicle for estudi in estudiant.estudis.all()]
            
            ofertes_rellevants = []
            for oferta in ofertes:
                if any(cicle in oferta.cicles.all() for cicle in cicles_estudiant):
                    ofertes_rellevants.append(oferta)
            
            if not ofertes_rellevants:
                continue
                
            num_candidatures = min(random.randint(2, 5), len(ofertes_rellevants))
            ofertes_seleccionades = random.sample(ofertes_rellevants, num_candidatures)
            
            for oferta in ofertes_seleccionades:
                estat_probabilitats = [
                    ('EP', 0.4),  # En procés
                    ('PR', 0.25),  # Preseleccionada
                    ('EN', 0.15),  # Entrevista programada
                    ('CO', 0.1),   # Contractada
                    ('RJ', 0.1),   # Rebutjada
                ]
                
                estat = random.choices(
                    [estat for estat, _ in estat_probabilitats],
                    weights=[prob for _, prob in estat_probabilitats]
                )[0]
                
                carta = f"Estimats senyors/es,\n\nEm dirigeixo a vostès per expressar el meu interès en la posició de {oferta.titol}. " \
                       f"Com a estudiant de {estudiant.estudis.first().cicle.nom if estudiant.estudis.exists() else 'formació professional'}, " \
                       f"crec que les meves habilitats encaixen amb els requisits.\n\nAtentament,\n{estudiant.usuari.get_full_name()}"
                
                candidatura = Candidatura.objects.create(
                    oferta=oferta,
                    estudiant=estudiant,
                    estat=estat,
                    carta_presentacio=carta,
                )
                
                if estat in ['PR', 'EN', 'CO', 'RJ']:
                    notes_exemples = [
                        "Bon perfil tècnic, molt motivat/da.",
                        "Entrevista positiva, bones habilitats.",
                        "Candidat/a destacat/da.",
                        "Necessita més experiència.",
                        "Excel·lent actitud."
                    ]
                    
                    candidatura.notes_empresa = random.choice(notes_exemples)
                    
                    if estat != 'RJ':
                        candidatura.puntuacio = random.randint(60, 95)
                    
                    candidatura.save()
                
                candidatures_creades += 1
        
        self.stdout.write(f"Candidatures creades: {candidatures_creades}")

    def crear_noticies(self):
        """Crea notícies de prova"""
        self.stdout.write("Creant notícies...")
        
        noticies = [
            {
                'titol': 'Nova edició de la Borsa de Treball',
                'descripcio': 'S\'obre el període per a la propera edició de la Borsa de Treball',
                'destinatari': 'TOTHOM'
            },
            {
                'titol': 'Taller de preparació de CV',
                'descripcio': 'Taller pràctic per millorar el teu currículum',
                'destinatari': 'ESTUDIANTS'
            },
            {
                'titol': 'Guia per a empreses participants',
                'descripcio': 'Tota la informació per a les empreses que vulguin participar',
                'destinatari': 'EMPRESES'
            }
        ]
        
        for noticia in noticies:
            Noticia.objects.create(
                titol=noticia['titol'],
                descripcio=noticia['descripcio'],
                cos=fake.text(max_nb_chars=1000),
                destinatari=noticia['destinatari'],
                data_publicacio=now(),
                visible=True
            )
        
        self.stdout.write(f"Notícies creades: {len(noticies)}")

    def mostrar_resum(self):
        """Mostra un resum de les dades creades"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("RESUM DE DADES CREADES:")
        self.stdout.write("="*50)
        self.stdout.write(f"Usuaris: {Usuari.objects.count()}")
        self.stdout.write(f"Empreses: {Empresa.objects.count()}")
        self.stdout.write(f"Estudiants: {Estudiant.objects.count()}")
        self.stdout.write(f"Estudis: {EstudiEstudiant.objects.count()}")
        self.stdout.write(f"Ofertes: {Oferta.objects.count()}")
        self.stdout.write(f"Candidatures: {Candidatura.objects.count()}")
        self.stdout.write(f"Notícies: {Noticia.objects.count()}")
        self.stdout.write("\nCredencials:")
        self.stdout.write("Admin: admin@vidalbarraquer.cat / admin123")
        self.stdout.write("Empreses: empresa1@empresa.com / empresa123")
        self.stdout.write("Estudiants: estudiant1@exemple.com / estudiant123")
        self.stdout.write("="*50)