from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import transaction
from faker import Faker
import random
from datetime import date
from borsa_treball.models import (
    Usuari, Empresa, Estudiant, Oferta, Cicle, Sector,
    EstudiEstudiant, CapacitatClau, CapacitatOferta,
    Funcio, NivellIdioma, Candidatura
)

fake = Faker('es_ES')

class Command(BaseCommand):
    help = 'Seeder per crear una empresa, 10 estudiants, 6 ofertes i 6 candidatures'

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            self.stdout.write("Iniciant seeder de test...")

            empresa = self.crear_empresa()
            estudiants = self.crear_estudiants()
            ofertes = self.crear_ofertes(empresa)
            self.crear_candidatures(estudiants, ofertes)

            self.stdout.write(self.style.SUCCESS("Seeder executat correctament!"))

    def crear_empresa(self):
        email = 'testempresa@empresa.com'

        usuari, _ = Usuari.objects.get_or_create(
            email=email,
            defaults={
                'nom': 'Test',
                'cognoms': 'Empresa',
                'tipus': 'EMP',
                'password': make_password('empresa123'),
                'telefon': fake.phone_number()[:15],
                'adreca': fake.address(),
            }
        )

        sector = Sector.objects.order_by('?').first()

        empresa, _ = Empresa.objects.get_or_create(
            usuari=usuari,
            defaults={
                'cif': f'B{fake.random_number(digits=8)}',
                'nom_comercial': 'Empresa Test Seeder',
                'rao_social': 'Empresa Test Seeder S.L.',
                'sector': sector,
                'descripcio': fake.text(max_nb_chars=200),
                'num_treballadors': 42,
                'web': 'https://www.testempresa.com',
                'telefon': fake.phone_number()[:15]
            }
        )

        self.stdout.write(f"Empresa creada: {empresa.nom_comercial}")
        return empresa

    def crear_estudiants(self):
        estudiants = []
        cicles = list(Cicle.objects.all())

        for i in range(10):
            email = f'testestudiant{i+1}@estudiant.com'
            dni = f'{fake.random_number(digits=8)}A'

            usuari, _ = Usuari.objects.get_or_create(
                email=email,
                defaults={
                    'nom': fake.first_name(),
                    'cognoms': fake.last_name(),
                    'tipus': 'EST',
                    'password': make_password('estudiant123'),
                    'telefon': fake.phone_number()[:15],
                    'adreca': fake.address(),
                    'data_naixement': fake.date_of_birth(minimum_age=18, maximum_age=25)
                }
            )

            estudiant, _ = Estudiant.objects.get_or_create(
                usuari=usuari,
                defaults={'dni': dni}
            )

            cicle = random.choice(cicles)
            EstudiEstudiant.objects.get_or_create(
                estudiant=estudiant,
                cicle=cicle,
                any_inici=2023,
                centre_estudis='Institut de Prova'
            )

            estudiants.append(estudiant)

        self.stdout.write(f"Creats {len(estudiants)} estudiants")
        return estudiants

    def crear_ofertes(self, empresa):
        ofertes = []
        cicles = list(Cicle.objects.all())
        capacitats = list(CapacitatClau.objects.all())

        for i in range(6):
            oferta = Oferta.objects.create(
                empresa=empresa,
                titol=f"Oferta Test {i+1}",
                descripcio=fake.text(300),
                data_publicacio=date.today(),
                data_limit=fake.future_date(end_date="+60d"),
                tipus_contracte='TI',
                jornada='CO',
                horari='De 9:00 a 14:00',
                salari='1200€/mes',
                requisits='Formació relacionada i ganes de treballar',
                lloc_treball=fake.city(),
                contacte_nom=fake.name(),
                contacte_email=fake.email(),
                contacte_telefon=fake.phone_number()[:15],
                estat='OC'
            )

            oferta.cicles.set(random.sample(cicles, k=1))
            oferta.capacitats_clau.set(random.sample(capacitats, k=3))

            CapacitatOferta.objects.create(oferta=oferta, nom='Creativitat')
            Funcio.objects.create(oferta=oferta, descripcio='Tasques bàsiques relacionades', ordre=1)
            NivellIdioma.objects.create(oferta=oferta, idioma='Català', nivell='bàsic')

            ofertes.append(oferta)

        self.stdout.write("6 ofertes creades per a l'empresa")
        return ofertes

    def crear_candidatures(self, estudiants, ofertes):
        oferta_obj = ofertes[0]  # Ens assegurem que la primera tingui 6 candidatures

        for i in range(6):
            est = estudiants[i]
            candidatura, _ = Candidatura.objects.get_or_create(
                oferta=oferta_obj,
                estudiant=est,
                defaults={
                    'estat': 'EP',
                    'carta_presentacio': 'Molt interessat en aquesta oferta.',
                }
            )

        self.stdout.write("6 candidatures creades per a la primera oferta")

