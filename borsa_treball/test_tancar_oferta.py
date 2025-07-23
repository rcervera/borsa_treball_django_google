import json
import shutil
import tempfile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile

# Import your actual models and view
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
        self.addCleanup(override.disable)  # Això s'assegura que després del test es restaurin els settings

        # Sobreescriu el storage
        # Assegura't que el camp 'cv_adjunt' existeix al teu model Candidatura
        # i que PrivateMediaStorage està correctament configurat.
        # Aquesta línia pot causar problemes si el model ja s'ha carregat.
        # Una alternativa més robusta seria mockejar el storage a nivell de test.
        # Per ara, assumim que aquesta configuració és vàlida per al teu entorn de test.
        try:
            Candidatura._meta.get_field('cv_adjunt').storage = PrivateMediaStorage(
                location=self.temp_dir,
                base_url="/private_temp/"
            )
        except Exception as e:
            print(f"Warning: Could not override Candidatura.cv_adjunt storage. Error: {e}")
            # Potser ja s'ha inicialitzat, o el camp no existeix.
            # Per a tests, sovint és millor mockejar el comportament del fitxer.

        
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

        # Crear ofertes utilitzant Oferta.objects.create() i assignar cicles després
        self.oferta_activa = Oferta.objects.create(
            titol="Oferta Activa",
            descripcio="Descripció",
            lloc_treball="Lloc",
            data_publicacio=date(2023, 1, 1),
            data_limit=date(2024, 12, 31),
            estat="AC",
            valoracio_empresa="",
            empresa=self.empresa,
            tipus_contracte = "PR",
            jornada = "CO",           
            numero_vacants = 2,
        )
        self.oferta_activa.cicles.add(self.cicle) # Assignar cicles amb .add()

        self.oferta_tancada = Oferta.objects.create(
            titol="Oferta Tancada",
            descripcio="Descripció",
            lloc_treball="Lloc",
            data_publicacio=date(2023, 1, 1),
            data_limit=date(2024, 12, 31),
            estat="TC",
            valoracio_empresa="Valoració existent",
            empresa=self.empresa,
            tipus_contracte = "PR",
            jornada = "CO",           
            numero_vacants = 2,
        )
        self.oferta_tancada.cicles.add(self.cicle) # Assignar cicles amb .add()

        # Create Estudiants and Candidatures
        # Corregir el typo self.user_estudiant a self.user_estudiantX
        self.user_estudiant1 = Usuari.objects.create_user(email='estudiant1@test.com',password='password123',tipus='EST', nom='Joan', cognoms='Petit')
        self.user_estudiant2 = Usuari.objects.create_user(email='estudiant2@test.com',password='password123',tipus='EST', nom='Joan', cognoms='Petit')
        self.user_estudiant3 = Usuari.objects.create_user(email='estudiant3@test.com',password='password123',tipus='EST', nom='Joan', cognoms='Petit')
        self.user_estudiant4 = Usuari.objects.create_user(email='estudiant4@test.com',password='password123',tipus='EST', nom='Joan', cognoms='Petit')
        
        self.estudiant1 = Estudiant.objects.create(usuari=self.user_estudiant1,dni='12345678A')
        self.estudiant2 = Estudiant.objects.create(usuari=self.user_estudiant2,dni='23456789B')
        self.estudiant3 = Estudiant.objects.create(usuari=self.user_estudiant3,dni='34567890C')
        self.estudiant4 = Estudiant.objects.create(usuari=self.user_estudiant4,dni='45678901D')

        # Fitxer de prova per al CV (crear una nova instància per a cada ús)
        def create_cv_file(name="cv.pdf"):
            return SimpleUploadedFile(
                name,
                b"contingut del cv de prova",
                content_type="application/pdf"
            )
        
        # Candidatures for oferta_activa
        self.candidatura_co = Candidatura.objects.create(
            oferta=self.oferta_activa, 
            estudiant=self.estudiant1, 
            estat='CO', 
            cv_adjunt=create_cv_file("cv_co.pdf"), 
            carta_presentacio='Carta de presentació CO que ha de ser prou llarga per a que pugui passar la validació inicial.'
        )
        self.candidatura_rj = Candidatura.objects.create(
            oferta=self.oferta_activa, 
            estudiant=self.estudiant2, 
            estat='RJ', 
            cv_adjunt=create_cv_file("cv_rj.pdf"), 
            carta_presentacio='Carta de presentació RJ que ha de ser prou llarga per a que pugui passar la validació inicial.'
        )
        self.candidatura_ep = Candidatura.objects.create(
            oferta=self.oferta_activa, 
            estudiant=self.estudiant3, 
            estat='EP',
            cv_adjunt=create_cv_file("cv_ep.pdf"), 
            carta_presentacio='Carta de presentació EP que ha de ser prou llarga per a que pugui passar la validació inicial.'
        )
        self.candidatura_pr = Candidatura.objects.create(
            oferta=self.oferta_activa, 
            estudiant=self.estudiant4, 
            estat='PR',
            cv_adjunt=create_cv_file("cv_pr.pdf"), 
            carta_presentacio='Carta de presentació PR que ha de ser prou llarga per a que pugui passar la validació inicial.'
        )

        # Oferta with all candidatures in final state
        self.oferta_all_final = Oferta.objects.create(
            titol="Oferta All Final",
            descripcio="Descripció",
            lloc_treball="Lloc",
            data_publicacio=date(2023, 1, 1),
            data_limit=date(2024, 12, 31),
            estat="AC",
            valoracio_empresa="",
            empresa=self.empresa,
            tipus_contracte = "PR",
            jornada = "CO",           
            numero_vacants = 2,
        )
        self.oferta_all_final.cicles.add(self.cicle) # Assignar cicles amb .add()
        Candidatura.objects.create(id=5, oferta=self.oferta_all_final, estudiant=self.estudiant1, estat='CO', cv_adjunt=create_cv_file("cv_final1.pdf"), carta_presentacio='Carta final 1.')
        Candidatura.objects.create(id=6, oferta=self.oferta_all_final, estudiant=self.estudiant2, estat='RJ', cv_adjunt=create_cv_file("cv_final2.pdf"), carta_presentacio='Carta final 2.')

        # Oferta with no candidatures
        self.oferta_no_candidatures = Oferta.objects.create(
            titol="Oferta No Candidatures",
            descripcio="Desc",
            lloc_treball="Lloc",
            data_publicacio=date(2023, 1, 1),
            data_limit=date(2024, 12, 31),
            estat="AC",
            valoracio_empresa="",
            empresa=self.empresa,
            tipus_contracte = "PR",
            jornada = "CO",           
            numero_vacants = 2,
        )
        self.oferta_no_candidatures.cicles.add(self.cicle) # Assignar cicles amb .add()


    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)


    def test_toggle_to_tancada_success(self):
        """
        Comprova que l'oferta es tanca correctament quan la valoració és vàlida
        i totes les candidatures estan en estat final.
        """
        self.client.force_login(self.user_empresa) # Login with the created user
        url = reverse('toggle_estat_oferta', args=[self.oferta_all_final.id])
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
        # No cal mockejar save si utilitzes .create()
        # self.mock_oferta_save.assert_called_once()
        # Recarregar l'objecte per obtenir l'estat actualitzat de la DB
        self.oferta_all_final.refresh_from_db() 
        self.assertEqual(self.oferta_all_final.estat, 'TC')
        self.assertEqual(self.oferta_all_final.valoracio_empresa, 'Molt bona valoració del procés.')
        # self.assertIn('stats', data)
        # self.assertEqual(data['stats']['total'], 2)
        # self.assertEqual(data['stats']['contratades'], 1)
        # self.assertEqual(data['stats']['rebutjades'], 1)

    def test_toggle_to_tancada_no_candidatures_success(self):
        """
        Comprova que l'oferta es tanca correctament quan no hi ha candidatures
        i la valoració és vàlida.
        """
        self.client.force_login(self.user_empresa)
        url = reverse('toggle_estat_oferta', args=[self.oferta_no_candidatures.id])
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
        self.oferta_no_candidatures.refresh_from_db()
        self.assertEqual(self.oferta_no_candidatures.estat, 'TC')
        self.assertEqual(self.oferta_no_candidatures.valoracio_empresa, 'Oferta tancada sense candidatures.')
        # self.assertIn('stats', data)
        # self.assertEqual(data['stats']['total'], 0)


    def test_toggle_to_activa_success(self):
        """
        Comprova que l'oferta es reobre correctament.
        """
        self.client.force_login(self.user_empresa)
        url = reverse('toggle_estat_oferta', args=[self.oferta_tancada.id])
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
        self.oferta_tancada.refresh_from_db()
        self.assertEqual(self.oferta_tancada.estat, 'AC')
        self.assertEqual(self.oferta_tancada.valoracio_empresa, 'Valoració existent') # Check it's not cleared
        # self.assertIn('stats', data)

    def test_toggle_to_tancada_missing_valoracio(self):
        """
        Comprova que no es pot tancar l'oferta si la valoració és buida.
        """
        self.client.force_login(self.user_empresa)
        url = reverse('toggle_estat_oferta', args=[self.oferta_activa.id])
        payload = {
            'estat': 'TC',
            'valoracio': ''
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400) # Bad Request
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('La valoració és obligatòria', data['error'])
        self.oferta_activa.refresh_from_db()
        self.assertEqual(self.oferta_activa.estat, 'AC') # Should remain active

    def test_toggle_to_tancada_candidatures_not_final(self):
        """
        Comprova que no es pot tancar l'oferta si hi ha candidatures
        que no estan en estat final (CO o RJ).
        """
        self.client.force_login(self.user_empresa)
        url = reverse('toggle_estat_oferta', args=[self.oferta_activa.id])
        payload = {
            'estat': 'TC',
            'valoracio': 'Valoració de prova.'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400) # Bad Request
        data = response.json()
        print(data.stats)
        self.assertFalse(data['success'])
        self.assertIn('totes les candidatures han d\'estar en estat "Contractada" o "Rebutjada"', data['error'])
        self.oferta_activa.refresh_from_db()
        self.assertEqual(self.oferta_activa.estat, 'AC') # Should remain active

    def test_toggle_oferta_not_found(self):
        """
        Comprova el cas on l'oferta no existeix o no pertany a l'empresa de l'usuari.
        """
        self.client.force_login(self.user_empresa)
        url = reverse('toggle_estat_oferta', args=[999]) # Non-existent ID
        payload = {
            'estat': 'TC',
            'valoracio': 'Test'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Oferta no trobada', data['message'])

    def test_toggle_invalid_estat(self):
        """
        Comprova el cas on es proporciona un estat no vàlid.
        """
        self.client.force_login(self.user_empresa)
        url = reverse('toggle_estat_oferta', args=[self.oferta_activa.id])
        payload = {
            'estat': 'INVALID_STATE',
            'valoracio': 'Test'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Estat no vàlid proporcionat', data['error'])
        self.oferta_activa.refresh_from_db()
        self.assertEqual(self.oferta_activa.estat, 'AC') # Should remain active

    def test_toggle_invalid_json(self):
        """
        Comprova el cas on el format JSON de la petició és invàlid.
        """
        self.client.force_login(self.user_empresa)
        url = reverse('toggle_estat_oferta', args=[self.oferta_activa.id])
        response = self.client.post(url, "this is not json", content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Format de petició JSON invàlid', data['error'])
        self.oferta_activa.refresh_from_db()
        self.assertEqual(self.oferta_activa.estat, 'AC') # Should remain active

    def test_toggle_user_no_empresa(self):
        """
        Comprova el cas on l'usuari no té una empresa associada.
        """
        user_no_empresa = Usuari.objects.create_user(email='noempresa@test.com', password='password123', tipus='EST')
        # No assignem empresa a aquest usuari per simular el cas
        self.client.force_login(user_no_empresa)
        url = reverse('toggle_estat_oferta', args=[self.oferta_activa.id])  
        payload = {
            'estat': 'TC',
            'valoracio': 'Test'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('No tens permisos', data['error'])
        self.oferta_activa.refresh_from_db()
        self.assertEqual(self.oferta_activa.estat, 'AC') # Should remain active

    def test_toggle_unauthenticated(self):
        """
        Comprova que un usuari no autenticat no pot accedir a la vista.
        """
        url = reverse('toggle_estat_oferta', args=[self.oferta_activa.id])
        payload = {
            'estat': 'TC',
            'valoracio': 'Test'
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 302) # Redirect to login
        # No cal refresh_from_db() ja que no s'hauria d'haver modificat res
