import os
import shutil
import tempfile
from datetime import date
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch

# Canvia 'borsa_treball' pel nom real de la teva aplicació si fos diferent
from borsa_treball.models import EstatCandidatura, Usuari, Estudiant, Empresa, Sector, Oferta, Candidatura

from borsa_treball.storages import PrivateMediaStorage

# Sobreescrivim la configuració de MEDIA_ROOT per a les proves.
# Això crea una carpeta temporal per als fitxers pujats durant els tests
# i evita problemes de permisos.
temp_dir = tempfile.mkdtemp()

# @patch('borsa_treball.storages.settings.PRIVATE_MEDIA_ROOT', new=tempfile.mkdtemp())
class AfegirCandidaturaAPITestCase(TestCase):
    """
    Conjunt de proves per a l'endpoint de l'API afegir_candidatura_api,
    adaptat a un model d'usuari personalitzat i amb correccions d'errors.
    """
    


    def setUp(self):
        """
        Configuració inicial per a totes les proves. S'executa abans de cada test.
        """
        self.client = Client()
        self.temp_dir = tempfile.mkdtemp()

        # Assigna el setting manualment abans de cridar el storage
        override = override_settings(PRIVATE_MEDIA_ROOT=self.temp_dir)
        override.enable()
        self.addCleanup(override.disable)  # Això s'assegura que després del test es restauren els settings

        # Sobreescriu el storage
        Candidatura._meta.get_field('cv_adjunt').storage = PrivateMediaStorage(
            location=self.temp_dir,
            base_url="/private_temp/"
        )

        # --- Creació d'usuaris amb el model personalitzat ---
        # 1. Usuari que és un estudiant
        self.user_estudiant = Usuari.objects.create_user(
            email='estudiant@test.com',
            password='password123',
            tipus='EST',
            nom='Joan',
            cognoms='Petit'
        )
        self.estudiant = Estudiant.objects.create(
            usuari=self.user_estudiant,
            dni='12345678A'
        )

        # 2. Usuari que NO és un estudiant (per exemple, un administrador)
        self.user_no_estudiant = Usuari.objects.create_user(
            email='admin@test.com',
            password='password123',
            tipus='ADM'
        )
        
        # 3. Usuari d'empresa per poder crear ofertes
        self.user_empresa = Usuari.objects.create_user(
            email='empresa@test.com',
            password='password123',
            tipus='EMP'
        )
        self.sector = Sector.objects.create(nom='Tecnologia')
        self.empresa = Empresa.objects.create(
            usuari=self.user_empresa,
            cif='A12345678',
            nom_comercial='Empresa de Prova',
            rao_social='Empresa de Prova SL',
            sector=self.sector
        )

        # --- Creació d'ofertes associades a l'empresa ---
        # Oferta activa
        self.oferta_activa = Oferta.objects.create(
            empresa=self.empresa,
            titol='Desenvolupador Python Junior',
            descripcio='Una gran oportunitat.',
            estat='AC',  # AC = Activa
            data_limit=date(2025, 12, 31),
            lloc_treball='Remot',
            tipus_contracte='IN',
            jornada='CO'
        )

        # Oferta inactiva
        self.oferta_inactiva = Oferta.objects.create(
            empresa=self.empresa,
            titol='Dissenyador Gràfic',
            descripcio='Oferta tancada.',
            estat='TC',  # TC = Tancada
            data_limit=date(2025, 1, 1),
            lloc_treball='Oficina',
            tipus_contracte='PR',
            jornada='PA'
        )

        # URL de l'API
        self.url_activa = reverse('afegir_candidatura_api', args=[self.oferta_activa.id])
        self.url_inactiva = reverse('afegir_candidatura_api', args=[self.oferta_inactiva.id])

        # Fitxer de prova per al CV
        self.cv_file = SimpleUploadedFile(
            "cv.pdf",
            b"contingut del cv de prova",
            content_type="application/pdf"
        )
        self.cv_file.seek(0)
        
        # Dades de prova per a una candidatura vàlida
        self.valid_data = {
            'carta_presentacio': 'Aquesta és una carta de presentació prou llarga per passar la validació inicial i demostrar el meu interès.',
            'cv_adjunt': self.cv_file,
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_creacio_candidatura_exitosa(self):
        """
        Verifica que un estudiant autenticat pot crear una candidatura amb èxit.
        """
        self.client.login(email='estudiant@test.com', password='password123')
        # Cal tornar a obrir el fitxer o clonar-lo per a cada petició POST
        cv_file_copy = SimpleUploadedFile(self.cv_file.name, self.cv_file.read(), content_type=self.cv_file.content_type)
        data = self.valid_data.copy()
        data['cv_adjunt'] = cv_file_copy
        
        response = self.client.post(self.url_activa, data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['message'], 'Candidatura enviada correctament!')
        self.assertTrue(Candidatura.objects.filter(estudiant=self.estudiant, oferta=self.oferta_activa).exists())

    def test_usuari_no_autenticat(self):
        """
        Verifica que un usuari no autenticat és redirigit a la pàgina de login.
        """
        response = self.client.post(self.url_activa, self.valid_data)
        self.assertEqual(response.status_code, 302)
        # S'ajusta per comprovar l'inici de la URL, fent-ho més flexible
        self.assertTrue(response.url.startswith('/login/'))

    def test_usuari_no_estudiant(self):
        """
        Verifica que un usuari autenticat però sense perfil d'estudiant rep un error 403.
        """
        self.client.login(email='admin@test.com', password='password123')
        response = self.client.post(self.url_activa, self.valid_data)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'No tens permisos per presentar candidatures.')

    def test_metode_no_permes(self):
        """
        Verifica que només s'accepten peticions POST.
        """
        self.client.login(email='estudiant@test.com', password='password123')
        response = self.client.get(self.url_activa)
        self.assertEqual(response.status_code, 405)

    def test_oferta_no_trobada(self):
        """
        Verifica que es retorna un 404 si l'ID de l'oferta no existeix.
        """
        self.client.login(email='estudiant@test.com', password='password123')
        url_inexistent = reverse('afegir_candidatura_api', args=[999])
        response = self.client.post(url_inexistent, self.valid_data)
        self.assertEqual(response.status_code, 404)

    def test_oferta_no_activa(self):
        """
        Verifica que es retorna un 404 si l'oferta no està en estat 'AC'.
        """
        self.client.login(email='estudiant@test.com', password='password123')
        response = self.client.post(self.url_inactiva, self.valid_data)
        self.assertEqual(response.status_code, 404)

    def test_candidatura_duplicada(self):
        """
        Verifica que un estudiant no pot aplicar dues vegades a la mateixa oferta.
        """
        Candidatura.objects.create(
            oferta=self.oferta_activa,
            estudiant=self.estudiant,
            carta_presentacio='Primera aplicació.',
            cv_adjunt=SimpleUploadedFile("cv1.pdf", b"contingut")
        )
        self.client.login(email='estudiant@test.com', password='password123')
        
        cv_file_copy = SimpleUploadedFile(self.cv_file.name, self.cv_file.read(), content_type=self.cv_file.content_type)
        data = self.valid_data.copy()
        data['cv_adjunt'] = cv_file_copy
        
        response = self.client.post(self.url_activa, data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Ja has presentat una candidatura a aquesta oferta.')

    def test_errors_de_validacio(self):
        """
        Verifica tots els possibles errors de validació dels camps.
        """
        self.client.login(email='estudiant@test.com', password='password123')
        
        # Cas 1: Carta de presentació buida
        data = self.valid_data.copy()
        data['carta_presentacio'] = ''
        response = self.client.post(self.url_activa, data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['errors']['carta_presentacio'], 'La carta de presentació és obligatòria.')

        # Cas 2: Carta de presentació massa curta
        data = self.valid_data.copy()
        data['carta_presentacio'] = 'curta'
        response = self.client.post(self.url_activa, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('La carta ha de tenir almenys 50 caràcters.', response.json()['errors']['carta_presentacio'])

        # Cas 3: CV no adjuntat
        data = {'carta_presentacio': self.valid_data['carta_presentacio']}
        response = self.client.post(self.url_activa, data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['errors']['cv_adjunt'], 'Heu d\'adjuntar el vostre Currículum Vitae.')

    # S'ha corregit el nom de l'app de 'la_teva_app' a 'borsa_treball'
    @patch('borsa_treball.views.Candidatura.objects.create')
    def test_error_inesperat_al_guardar(self, mock_create):
        """
        Verifica que es gestiona correctament un error inesperat en crear la candidatura.
        """
        mock_create.side_effect = Exception("Error de base de dades simulat")
        self.client.login(email='estudiant@test.com', password='password123')
        
        cv_file_copy = SimpleUploadedFile(self.cv_file.name, self.cv_file.read(), content_type=self.cv_file.content_type)
        data = self.valid_data.copy()
        data['cv_adjunt'] = cv_file_copy
        
        response = self.client.post(self.url_activa, data)
        self.assertEqual(response.status_code, 500)
        self.assertIn('Error inesperat en desar la candidatura', response.json()['error'])

