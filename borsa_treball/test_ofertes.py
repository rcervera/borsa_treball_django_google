import json
import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

# --- Models de suport (mínims per fer funcionar el test) ---
# En el teu projecte real, aquests models ja existiran i només caldrà importar-los.
Usuari = get_user_model()

# Importem els models necessaris, incloent el nou FamiliaProfessional
from .models import Empresa, FamiliaProfessional, Cicle, Oferta, CapacitatOferta, Funcio, NivellIdioma, RegistreAuditoria

# --- Comença la classe del Test ---

class CrearOfertaAPITestCase(TestCase):

    def setUp(self):
        """
        Configuració inicial que s'executa abans de cada test.
        """
        self.client = Client()

        # 1. Crear usuari i empresa
        self.user_empresa = Usuari.objects.create_user(
            email='empresa@test.com',
            password='password123',
            tipus='EMP'
        )
        self.empresa = Empresa.objects.create(
            user=self.user_empresa,
            nom_comercial="Empresa de Prova, S.L.",
            cif="B12345678"
        )
        
        # 2. Crear un altre usuari (no empresa)
        self.user_normal = Usuari.objects.create_user(
            email='estudiant@test.com',
            password='password123',
            tipus='EST'
        )

        # 3. Crear Família Professional 
        # Aquest pas és necessari abans de poder crear un Cicle.
        self.familia_informatica = FamiliaProfessional.objects.create(
            codi="IFC",
            nom="Informàtica i Comunicacions"
        )

        # 4. Crear cicles formatius 
        # Ara associem cada cicle a la seva família professional.
        self.cicle1 = Cicle.objects.create(
            familia=self.familia_informatica,
            codi="DAW",
            nom="Desenvolupament d'Aplicacions Web",
            grau="GS", # Grau Superior
            durada=2000
        )
        self.cicle2 = Cicle.objects.create(
            familia=self.familia_informatica,
            codi="SMIX",
            nom="Sistemes Microinformàtics i Xarxes",
            grau="GM", # Grau Mitjà
            durada=2000
        )

        # 5. URL de l'API
        self.url = reverse('crear_oferta_api')

        # 6. Dades vàlides per a la petició (sense canvis)
        self.data_limit_futura = (timezone.now().date() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        self.valid_data = {
            "titol": "Desenvolupador/a Django Junior",
            "descripcio": "Busquem un desenvolupador apassionat per Django.",
            "data_limit": self.data_limit_futura,
            "tipus_contracte": "PR",
            "jornada": "CO",
            "lloc_treball": "Barcelona",
            "numero_vacants": 2,
            "cicles": [self.cicle1.id, self.cicle2.id],
            "destinatari": "EST",
            "experiencia": "SE",
            "requisits": "Coneixements de Python i Django.",
            "horari": "9h a 18h",
            "salari": "18.000€ - 22.000€ bruts/any",
            "visible": True,
            "capacitatsLliures": ["Proactivitat", "Treball en equip"],
            "funcions": ["Desenvolupar noves funcionalitats.", "Manteniment de codi existent."],
            "idiomes": [
                {"idioma": "Anglès", "nivell": "alt"},
                {"idioma": "Català", "nivell": "nadiu"}
            ]
        }

    # =========================================================
    # Tests per a la creació d'ofertes
    # =========================================================

    def test_crear_oferta_exitosa(self):
        """
        Verifica que una oferta es pot crear correctament amb totes les dades vàlides.
        """
        self.client.login(email='empresa@test.com', password='password123')
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertTrue(response_data['success'])
        self.assertEqual(Oferta.objects.count(), 1)
        oferta = Oferta.objects.first()
        self.assertEqual(oferta.titol, self.valid_data['titol'])
        self.assertEqual(oferta.empresa, self.empresa)
        self.assertEqual(oferta.cicles.count(), 2)


    def test_error_camps_obligatoris_buits(self):
        """
        Verifica que la API retorna un error específic per a cada camp
        obligatori quan s'envia buit.
        """
        self.client.login(email='empresa@test.com', password='password123')

        # Dades amb tots els camps obligatoris definits com a buits
        data_invalida = {
            "titol": "",
            "descripcio": "",
            "data_limit": "",
            "tipus_contracte": "",
            "jornada": "",
            "lloc_treball": "",
            "numero_vacants": "",
            "cicles": [],
            # Els camps opcionals no cal validar-los aquí
            "destinatari": "",
            "experiencia": "",
            "requisits": "",
            "horari": "",
            "salari": "",
        }

        response = self.client.post(self.url, data=json.dumps(data_invalida), content_type='application/json')

        # 1. Comprovar que la resposta és un error de validació (400)
        self.assertEqual(response.status_code, 400)

        # 2. Obtenir el diccionari d'errors de la resposta JSON
        errors = response.json().get('errors', {})
        self.assertFalse(response.json()['success'])

        # 3. Comprovar cada missatge d'error específic per a cada camp obligatori
        self.assertEqual(errors.get('titol'), "El títol és obligatori.")
        self.assertEqual(errors.get('descripcio'), "La descripció és obligatòria.")
        self.assertEqual(errors.get('data_limit'), "La data límit és obligatòria.")
        self.assertEqual(errors.get('tipus_contracte'), "Tipus de contracte obligatori.")
        self.assertEqual(errors.get('jornada'), "Jornada obligatòria.")
        self.assertEqual(errors.get('lloc_treball'), "Lloc de treball obligatori.")
        self.assertEqual(errors.get('numero_vacants'), "Cal indicar el nombre de vacants.")
        self.assertEqual(errors.get('cicles'), "Has de seleccionar almenys un cicle.")

        # 4. Assegurar que l'oferta NO s'ha creat a la base de dades
        self.assertEqual(Oferta.objects.count(), 0)

    def test_error_data_limit_passada(self):
        """
        Verifica que no es pot crear una oferta amb una data límit passada.
        """
        self.client.login(
    def test_usuari_no_autenticat(self):
        """
        Verifica que un usuari no autenticat és redirigit.
        """
        response = self.client.post(self.url, data=json.dumps(self.valid_data), content_type='application/json')
        self.assertEqual(response.status_code, 302)

    def test_usuari_sense_empresa_associada(self):
        """
        Verifica que un usuari sense empresa no pot crear ofertes.
        """
        self.client.login(email='estudiant@test.com', password='password123')
        response = self.client.post(self.url, data=json.dumps(self.valid_data), content_type='application/json')
        self.assertEqual(response.status_code, 200) # La teva vista retorna 200 amb error JSON
        response_data = response.json()
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
        self.assertEqual(Oferta.objects.count(), 0)