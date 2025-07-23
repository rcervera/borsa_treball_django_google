import json
import shutil
import tempfile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile

from borsa_treball.models import Empresa, Oferta, Candidatura, Estudiant, Sector, Usuari, FamiliaProfessional, Cicle
from borsa_treball.storages import PrivateMediaStorage
from borsa_treball.views_empresa import toggle_tancament_oferta


class ToggleOfertaStatusTest(TestCase):
    def setUp(self):
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

        
         # 1. Crear usuari i empresa
        self.user_empresa = Usuari.objects.create_user(
            email='empresa@test.com',
            password='password123',
            tipus='EMP'
        )
        self.sector = Sector.objects.create(nom='Tecnologia')
        self.empresa = Empresa.objects.create(
            usuari=self.user_empresa,
            nom_comercial="Empresa de Prova, S.L.",
            cif="B12345678",            
            rao_social='Empresa de Prova SL',
            sector=self.sector
        )
        
        self.familia_informatica = FamiliaProfessional.objects.create(
            codi="IFC",
            nom="Informàtica i Comunicacions"
        )

        self.cicle = Cicle.objects.create(
            familia=self.familia_informatica,
            codi="DAW",
            nom="Desenvolupament d'Aplicacions Web",
            grau="GS", # Grau Superior
            durada=2000
        )

        self.oferta_activa = Oferta(
            id=1,
            titol="Oferta Activa",
            descripcio="Descripció",
            lloc_treball="Lloc",
            data_publicacio=date(2023, 1, 1),
            data_limit=date(2024, 12, 31),
            estat="AC",
            valoracio_empresa="",
            empresa=self.empresa,
            cicles= [self.cicle.id],
            tipus_contracte = "PR",
            jornada = "CO",           
            numero_vacants = 2,
        )
        Oferta.objects.append(self.oferta_activa)

        self.oferta_tancada = Oferta(
            id=2,
            titol="Oferta Tancada",
            descripcio="Descripció",
            lloc_treball="Lloc",
            data_publicacio=date(2023, 1, 1),
            data_limit=date(2024, 12, 31),
            estat="TC",
            valoracio_empresa="Valoració existent",
            empresa=self.empresa,
            cicles= [self.cicle.id],
            tipus_contracte = "PR",
            jornada = "CO",           
            numero_vacants = 2,
        )
        Oferta.objects.append(self.oferta_tancada)

        # Create Estudiants and Candidatures
        self.user_estudiant1 = Usuari.objects.create_user(email='estudiant1@test.com',password='password123',tipus='EST', nom='Joan', cognoms='Petit')
        self.user_estudiant2 = Usuari.objects.create_user(email='estudiant2@test.com',password='password123',tipus='EST', nom='Joan', cognoms='Petit')
        self.user_estudiant3 = Usuari.objects.create_user(email='estudiant3@test.com',password='password123',tipus='EST', nom='Joan', cognoms='Petit')
        self.user_estudiant4 = Usuari.objects.create_user(email='estudiant4@test.com',password='password123',tipus='EST', nom='Joan', cognoms='Petit')
        
        self.estudiant1 = Estudiant.objects.create(usuari=self.user_estudiant,dni='12345678A')
        self.estudiant2 = Estudiant.objects.create(usuari=self.user_estudiant2,dni='23456789B')
        self.estudiant3 = Estudiant.objects.create(usuari=self.user_estudiant3,dni='34567890C')
        self.estudiant4 = Estudiant.objects.create(usuari=self.user_estudiant4,dni='45678901D')

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

        # Candidatures for oferta_activa
        self.candidatura_co = Candidatura(id=1, oferta=self.oferta_activa, estudiant=self.estudiant1, estat='CO', cv_adjunt=self.cv_file, carta_presentacio='Carta de presentació CO que ha de ser prou llarga per a que pugui passar la validació inicial.')
        self.candidatura_rj = Candidatura(id=2, oferta=self.oferta_activa, estudiant=self.estudiant2, estat='RJ', cv_adjunt=self.cv_file, carta_presentacio='Carta de presentació RJ que ha de ser prou llarga per a que pugui passar la validació inicial.')
        self.candidatura_ep = Candidatura(id=3, oferta=self.oferta_activa, estudiant=self.estudiant3, estat='EP',cv_adjunt=self.cv_file, carta_presentacio='Carta de presentació EP que ha de ser prou llarga per a que pugui passar la validació inicial.')
        self.candidatura_pr = Candidatura(id=4, oferta=self.oferta_activa, estudiant=self.estudiant4, estat='PR',cv_adjunt=self.cv_file, carta_presentacio='Carta de presentació PR que ha de ser prou llarga per a que pugui passar la validació inicial.')

        self.oferta_activa._candidatures = [
            self.candidatura_co,
            self.candidatura_rj,
            self.candidatura_ep,
            self.candidatura_pr,
        ]

        # Oferta with all candidatures in final state
        self.oferta_all_final = Oferta(
            id=3,
            titol="Oferta All Final",
            descripcio="Descripció",
            lloc_treball="Lloc",
            data_publicacio=date(2023, 1, 1),
            data_limit=date(2024, 12, 31),
            estat="AC",
            valoracio_empresa="",
            empresa=self.empresa,
            cicles= [self.cicle.id],
            tipus_contracte = "PR",
            jornada = "CO",           
            numero_vacants = 2,
        )
        Oferta.objects.append(self.oferta_all_final)
        self.oferta_all_final._candidatures = [
            Candidatura(id=5, oferta=self.oferta_all_final, estudiant=self.estudiant1, estat='CO'),
            Candidatura(id=6, oferta=self.oferta_all_final, estudiant=self.estudiant2, estat='RJ'),
        ]

        # Oferta with no candidatures
        self.oferta_no_candidatures = Oferta(
            id=4,
            titol="Oferta No Candidatures",
            descripcio="Desc",
            lloc_treball="Lloc",
            data_publicacio=date(2023, 1, 1),
            data_limit=date(2024, 12, 31),
            estat="AC",
            valoracio_empresa="",
            empresa=self.empresa,
            cicles= [self.cicle.id],
            tipus_contracte = "PR",
            jornada = "CO",           
            numero_vacants = 2,
        )
        Oferta.objects.append(self.oferta_no_candidatures)
        self.oferta_no_candidatures._candidatures = []


    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)


    def test_toggle_to_tancada_success(self):
        """
        Comprova que l'oferta es tanca correctament quan la valoració és vàlida
        i totes les candidatures estan en estat final.
        """
        self.client.force_login(self.user)
        url = reverse('toggle_oferta_estat', args=[self.oferta_all_final.id])
        payload = {
            'estat': 'TC',
            'valoracio': 'Molt bona valoració del procés.'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['estat'], 'TC')
        self.assertEqual(data['valoracio'], 'Molt bona valoració del procés.')
        self.assertIn('message', data)
        self.mock_oferta_save.assert_called_once()
        self.assertEqual(self.oferta_all_final.estat, 'TC')
        self.assertEqual(self.oferta_all_final.valoracio_empresa, 'Molt bona valoració del procés.')
        self.assertIn('stats', data)
        self.assertEqual(data['stats']['total'], 2)
        self.assertEqual(data['stats']['contratades'], 1)
        self.assertEqual(data['stats']['rebutjades'], 1)

    def test_toggle_to_tancada_no_candidatures_success(self):
        """
        Comprova que l'oferta es tanca correctament quan no hi ha candidatures
        i la valoració és vàlida.
        """
        self.client.force_login(self.user)
        url = reverse('toggle_oferta_estat', args=[self.oferta_no_candidatures.id])
        payload = {
            'estat': 'TC',
            'valoracio': 'Oferta tancada sense candidatures.'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['estat'], 'TC')
        self.assertEqual(data['valoracio'], 'Oferta tancada sense candidatures.')
        self.mock_oferta_save.assert_called_once()
        self.assertEqual(self.oferta_no_candidatures.estat, 'TC')
        self.assertEqual(self.oferta_no_candidatures.valoracio_empresa, 'Oferta tancada sense candidatures.')
        self.assertIn('stats', data)
        self.assertEqual(data['stats']['total'], 0)


    def test_toggle_to_activa_success(self):
        """
        Comprova que l'oferta es reobre correctament.
        """
        self.client.force_login(self.user)
        url = reverse('toggle_oferta_estat', args=[self.oferta_tancada.id])
        payload = {
            'estat': 'AC',
            'valoracio': '' # Valoració no rellevant en re-obertura, però s'envia
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['estat'], 'AC')
        # Valoració ha de mantenir-se com estava abans de re-obrir
        self.assertEqual(data['valoracio'], 'Valoració existent')
        self.assertIn('message', data)
        self.mock_oferta_save.assert_called_once()
        self.assertEqual(self.oferta_tancada.estat, 'AC')
        self.assertEqual(self.oferta_tancada.valoracio_empresa, 'Valoració existent') # Check it's not cleared
        self.assertIn('stats', data)

    def test_toggle_to_tancada_missing_valoracio(self):
        """
        Comprova que no es pot tancar l'oferta si la valoració és buida.
        """
        self.client.force_login(self.user)
        url = reverse('toggle_oferta_estat', args=[self.oferta_activa.id])
        payload = {
            'estat': 'TC',
            'valoracio': ''
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400) # Bad Request
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('La valoració és obligatòria', data['error'])
        self.mock_oferta_save.assert_not_called()
        self.assertEqual(self.oferta_activa.estat, 'AC') # Should remain active

    def test_toggle_to_tancada_candidatures_not_final(self):
        """
        Comprova que no es pot tancar l'oferta si hi ha candidatures
        que no estan en estat final (CO o RJ).
        """
        self.client.force_login(self.user)
        url = reverse('toggle_oferta_estat', args=[self.oferta_activa.id])
        payload = {
            'estat': 'TC',
            'valoracio': 'Valoració de prova.'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400) # Bad Request
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('totes les candidatures han d\'estar en estat "Contractada" o "Rebutjada"', data['error'])
        self.mock_oferta_save.assert_not_called()
        self.assertEqual(self.oferta_activa.estat, 'AC') # Should remain active

    def test_toggle_oferta_not_found(self):
        """
        Comprova el cas on l'oferta no existeix o no pertany a l'empresa de l'usuari.
        """
        self.client.force_login(self.user)
        url = reverse('toggle_oferta_estat', args=[999]) # Non-existent ID
        payload = {
            'estat': 'TC',
            'valoracio': 'Test'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Oferta no trobada', data['message'])
        self.mock_oferta_save.assert_not_called()

    def test_toggle_invalid_estat(self):
        """
        Comprova el cas on es proporciona un estat no vàlid.
        """
        self.client.force_login(self.user)
        url = reverse('toggle_oferta_estat', args=[self.oferta_activa.id])
        payload = {
            'estat': 'INVALID_STATE',
            'valoracio': 'Test'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Estat no vàlid proporcionat', data['error'])
        self.mock_oferta_save.assert_not_called()

    def test_toggle_invalid_json(self):
        """
        Comprova el cas on el format JSON de la petició és invàlid.
        """
        self.client.force_login(self.user)
        url = reverse('toggle_oferta_estat', args=[self.oferta_activa.id])
        response = self.client.post(url, "this is not json", content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Format de petició JSON invàlid', data['error'])
        self.mock_oferta_save.assert_not_called()

    def test_toggle_user_no_empresa(self):
        """
        Comprova el cas on l'usuari no té una empresa associada.
        """
        user_no_empresa = User.objects.create_user(username='noempresa', password='password123')
        # Do not attach empresa to this user
        self.client.force_login(user_no_empresa)
        url = reverse('toggle_oferta_estat', args=[self.oferta_activa.id])
        payload = {
            'estat': 'TC',
            'valoracio': 'Test'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('No tens permisos', data['error'])
        self.mock_oferta_save.assert_not_called()

    def test_toggle_unauthenticated(self):
        """
        Comprova que un usuari no autenticat no pot accedir a la vista.
        """
        url = reverse('toggle_oferta_estat', args=[self.oferta_activa.id])
        payload = {
            'estat': 'TC',
            'valoracio': 'Test'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 302) # Redirect to login
        self.mock_oferta_save.assert_not_called()
