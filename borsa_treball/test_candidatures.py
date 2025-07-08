from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from datetime import timedelta
from django.utils.timezone import now
from .models import Usuari, Empresa, Sector, Cicle, Oferta, CapacitatClau, Candidatura

class AfegirCandidaturaTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Crear usuari estudiant i iniciar sessió
        self.usuari = Usuari.objects.create_user(
            email="estudiant@test.com",
            password="test1234",
            tipus="EST"
        )
        self.client.login(email="estudiant@test.com", password="test1234")

        # Crear sector, cicle, capacitat
        self.sector = Sector.objects.create(nom="Informàtica")
        self.cicle = Cicle.objects.create(nom="DAM")
        self.capacitat = CapacitatClau.objects.create(nom="Treball en equip")

        # Crear empresa
        self.empresa_user = Usuari.objects.create_user(
            email="empresa@test.com",
            password="empresa1234",
            tipus="EMP"
        )
        self.empresa = Empresa.objects.create(
            usuari=self.empresa_user,
            cif="B12345678",
            nom_comercial="TechCorp",
            rao_social="TechCorp SL",
            sector=self.sector
        )

        # Crear oferta
        self.oferta = Oferta.objects.create(
            empresa=self.empresa,
            titol="Desenvolupador Django",
            descripcio="Backend amb Django",
            numero_vacants=1,
            data_limit=now().date() + timedelta(days=15),
            lloc_treball="Barcelona",
            tipus_contracte='PR',
            jornada='CO',
            public_destinatari='EST',
            experiencia='SE',
            estat='AC',  # ACTIVA
            activa=True,
            visible=True
        )
        self.oferta.cicles.add(self.cicle)
        self.oferta.capacitats_clau.add(self.capacitat)

    def test_afegir_candidatura_api(self):
        url = reverse('afegir_oferta_api', args=[self.oferta.id])  

        cv_pdf = SimpleUploadedFile(
            "cv.pdf", b"%PDF-1.4 fake content", content_type="application/pdf"
        )

        response = self.client.post(url, {
            'cv': cv_pdf
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Candidatura.objects.count(), 1)
        candidatura = Candidatura.objects.first()
        self.assertEqual(candidatura.estudiant, self.usuari)
        self.assertEqual(candidatura.oferta, self.oferta)
        self.assertTrue(candidatura.cv.name.endswith('.pdf'))
