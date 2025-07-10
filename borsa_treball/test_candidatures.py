import os
import shutil
import tempfile
from datetime import date
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch

# Canvia 'borsa_treball' pel nom real de la teva aplicació si fos diferent
from borsa_treball.models import Usuari, Estudiant, Empresa, Sector, Oferta, Candidatura

# Sobreescrivim la configuració de MEDIA_ROOT per a les proves.
# Això crea una carpeta temporal per als fitxers pujats durant els tests
# i evita problemes de permisos.
temp_dir = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=temp_dir)
class AfegirCandidaturaAPITestCase(TestCase):
    """
    Conjunt de proves per a l'endpoint de l'API afegir_candidatura_api,
    adaptat a un model d'usuari personalitzat i amb correccions d'errors.
    """

    @classmethod
    def tearDownClass(cls):
        """
        S'executa un cop al final de totes les proves de la classe.
        Esborra la carpeta temporal creada per a MEDIA_ROOT.
        """
        shutil.rmtree(temp_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        """
        Configuració inicial per a totes les proves. S'executa abans de cada test.
        """
        self.client = Client()

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



@override_settings(MEDIA_ROOT=temp_dir)
class EditarCandidaturaAPITestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(temp_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        """
        Configura un estudiant, una empresa, una oferta i una candidatura editable.
        """
        self.client = Client()

        self.user_estudiant = Usuari.objects.create_user(
            email='edit@test.com',
            password='editpass123',
            tipus='EST',
            nom='Maria',
            cognoms='Casas'
        )
        self.estudiant = Estudiant.objects.create(usuari=self.user_estudiant, dni='99999999Z')

        self.user_empresa = Usuari.objects.create_user(
            email='empresa2@test.com',
            password='password123',
            tipus='EMP'
        )
        self.sector = Sector.objects.create(nom='Enginyeria')
        self.empresa = Empresa.objects.create(
            usuari=self.user_empresa,
            cif='B98765432',
            nom_comercial='Empresa Enginyeria',
            rao_social='Enginyeria SL',
            sector=self.sector
        )
        self.oferta = Oferta.objects.create(
            empresa=self.empresa,
            titol='Enginyer Elèctric',
            descripcio='Feina estable',
            estat='AC',
            data_limit=date(2025, 12, 31),
            lloc_treball='Barcelona',
            tipus_contracte='IN',
            jornada='CO'
        )

        self.cv_file = SimpleUploadedFile("cv_nou.pdf", b"cv actualitzat", content_type="application/pdf")

        self.candidatura = Candidatura.objects.create(
            estudiant=self.estudiant,
            oferta=self.oferta,
            carta_presentacio='Carta inicial molt vàlida i llarga.',
            estat='EP',  # EP = En procés
            cv_adjunt=self.cv_file
        )
        self.url = reverse('editar_candidatura_api', args=[self.candidatura.id])
        

    def test_edicio_correcta(self):
        """
        Verifica que un estudiant autenticat pot editar correctament la seva candidatura.
        """
        self.client.login(email='edit@test.com', password='editpass123')
        data = {
            'carta_presentacio': 'Aquesta és una nova carta de presentació vàlida que supera els 50 caràcters.',
            'cv_adjunt': self.cv_file
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['message'], 'Candidatura actualitzada correctament!')

    def test_no_autenticat(self):
        """
        Verifica que un usuari no autenticat és redirigit a la pàgina de login.
        """
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_no_es_estudiant(self):
        """
        Verifica que un usuari sense perfil d'estudiant no pot editar candidatures.
        """
        usuari_admin = Usuari.objects.create_user(email='admin@test.com', password='adminpass', tipus='ADM')
        self.client.login(email='admin@test.com', password='adminpass')
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 403)
        self.assertIn('No tens permisos', response.json()['error'])

    def test_candidatura_inexistent(self):
        """
        Verifica que es retorna un 404 si la candidatura no existeix.
        """
        self.client.login(email='edit@test.com', password='editpass123')
        url = reverse('editar_candidatura_api', args=[9999])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 404)

    def test_candidatura_no_en_proces(self):
        """
        Verifica que només es poden editar candidatures en estat 'EN_PROCES'.
        """
        self.candidatura.estat = 'PR'
        self.candidatura.save()
        self.client.login(email='edit@test.com', password='editpass123')
        response = self.client.post(self.url, {'carta_presentacio': 'Prova de carta.'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('no pots editar', response.json()['error'].lower())

    def test_errors_validacio(self):
        """
        Verifica que es gestionen correctament els errors de validació dels camps.
        """
        self.client.login(email='edit@test.com', password='editpass123')

        # Carta buida
        response = self.client.post(self.url, {'carta_presentacio': ''})
        self.assertEqual(response.status_code, 400)
        self.assertIn('és obligatòria', response.json()['errors']['carta_presentacio'])

        # Massa curta
        response = self.client.post(self.url, {'carta_presentacio': 'Curta'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('almenys 50 caràcters', response.json()['errors']['carta_presentacio'])

        # Massa llarga
        carta_llarga = 'a' * 2001
        response = self.client.post(self.url, {'carta_presentacio': carta_llarga})
        self.assertEqual(response.status_code, 400)
        self.assertIn('no pot superar els 2000', response.json()['errors']['carta_presentacio'])

        # Arxiu massa gran
        arxiu_gran = SimpleUploadedFile("cv.pdf", b"x" * (6 * 1024 * 1024), content_type="application/pdf")
        response = self.client.post(self.url, {
            'carta_presentacio': 'Carta vàlida amb més de 50 caràcters.',
            'cv_adjunt': arxiu_gran
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('CV no pot superar', response.json()['errors']['cv_adjunt'])

        # Tipus no vàlid
        arxiu_invalid = SimpleUploadedFile("cv.txt", b"Hola mon", content_type="text/plain")
        response = self.client.post(self.url, {
            'carta_presentacio': 'Carta vàlida amb més de 50 caràcters.',
            'cv_adjunt': arxiu_invalid
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('Format no vàlid', response.json()['errors']['cv_adjunt'])

   
    @patch('borsa_treball.views.Candidatura.save')
    def test_error_en_guardar(self, mock_save):
        """
        Verifica que es gestiona correctament un error inesperat en desar la candidatura.
        """
        mock_save.side_effect = Exception("Error inesperat")
        self.client.login(email='edit@test.com', password='editpass123')

        # CV vàlid (cal reiniciar o recrear el fitxer per evitar "stream closed")
        cv_file = SimpleUploadedFile("cv.pdf", b"Contingut valid", content_type="application/pdf")

        response = self.client.post(self.url, {
            'carta_presentacio': 'Carta vàlida amb suficients caràcters per passar la validació.',
            'cv_adjunt': cv_file
        })

        print(response.json())  # Opcional per debug
        self.assertEqual(response.status_code, 500)
        self.assertIn('error inesperat', response.json()['error'].lower())
