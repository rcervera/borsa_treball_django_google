from django.test import TestCase, Client
from django.urls import reverse
from .models import FamiliaProfessional, Usuari, Estudiant, EstudiEstudiant, Cicle, Empresa, Sector, RegistreAuditoria
from django.utils.timezone import now
import json

class RegistreEstudiantTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('registre_estudiant_api')
        
        # Crear una família professional
        self.familia = FamiliaProfessional.objects.create(
            nom='Informàtica i comunicacions'
        )

        # Crear un cicle associat
        self.cicle = Cicle.objects.create(
            familia=self.familia,
            codi='IFC01',
            nom='DAM',
            grau='GS',
            durada=2000  # per exemple, en hores
        )

    def test_registre_estudiant_correcte(self):
        dades = {
            "email": "test@student.com",
            "password1": "ContrasenyaSegura123",
            "password2": "ContrasenyaSegura123",
            "nom": "Test",
            "cognoms": "Estudiant",
            "dni": "12345678Z",
            "telefon": "+34600000000",
            "cicle": str(self.cicle.id),
            "any_inici": str(now().year - 2),
            "any_fi": str(now().year),
            "terms": True
        }

        response = self.client.post(self.url, data=json.dumps(dades), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['success'], True)
        self.assertTrue(Usuari.objects.filter(email="test@student.com").exists())
        self.assertTrue(Estudiant.objects.filter(dni="12345678Z").exists())
        self.assertEqual(EstudiEstudiant.objects.count(), 1)

    def test_registre_estudiant_email_duplicat(self):
        # Primer registre
        Usuari.objects.create_user(email="test@student.com", password="segura123", nom="Test", cognoms="Usuari", telefon="+34611111111", tipus='EST')
        
        dades = {
            "email": "test@student.com",
            "password1": "AltraContrasenya123",
            "password2": "AltraContrasenya123",
            "nom": "Nou",
            "cognoms": "Usuari",
            "dni": "87654321X",
            "telefon": "+34622222222",
            "cicle": str(self.cicle.id),
            "any_inici": str(now().year - 1),
            "any_fi": str(now().year),
            "terms": True
        }

        response = self.client.post(self.url, data=json.dumps(dades), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['success'], False)
        self.assertIn('email', response.json()['errors'])

    def test_registre_estudiant_dades_invalides(self):
        dades = {
            "email": "malformat",  # correu mal format
            "password1": "123",
            "password2": "456",  # contrasenyes diferents
            "nom": "",
            "cognoms": "",
            "dni": "BAD_DNI",
            "telefon": "abcdef",
            "cicle": "no_num",
            "any_inici": "3000",
            "any_fi": "1900",
            "terms": False
        }

        response = self.client.post(self.url, data=json.dumps(dades), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['success'], False)
        self.assertIn('email', response.json()['errors'])
        self.assertIn('password2', response.json()['errors'])
        self.assertIn('dni', response.json()['errors'])
        self.assertIn('telefon', response.json()['errors'])
        self.assertIn('terms', response.json()['errors'])


    def test_registre_estudiant_dni_duplicat(self):
            # Crear estudiant inicial
            usuari = Usuari.objects.create_user(email="usuari1@student.com", password="password123", nom="Usuari", cognoms="Un", telefon="+34611111111", tipus='EST')
            Estudiant.objects.create(usuari=usuari, dni="87654321X")

            dades = {
                "email": "nouestudiant@student.com",
                "password1": "ContrasenyaSegura123",
                "password2": "ContrasenyaSegura123",
                "nom": "Nou",
                "cognoms": "Estudiant",
                "dni": "87654321X",  # DNI duplicat
                "telefon": "+34622222222",
                "cicle": str(self.cicle.id),
                "any_inici": str(now().year - 1),
                "any_fi": str(now().year),
                "terms": True
            }
            response = self.client.post(self.url, data=json.dumps(dades), content_type='application/json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('dni', response.json()['errors'])
            self.assertIn('registrat', response.json()['errors']['dni'][0].lower())
            

    #  Validació anys (any_inici futur)
    def test_registre_any_inici_futur(self):
            futur = now().year + 1
            dades = {
                "email": "futur@student.com",
                "password1": "ContrasenyaSegura123",
                "password2": "ContrasenyaSegura123",
                "nom": "Futur",
                "cognoms": "Estudiant",
                "dni": "23456789A",
                "telefon": "+34600000001",
                "cicle": str(self.cicle.id),
                "any_inici": str(futur),  # any inici futur
                "any_fi": str(futur + 1),
                "terms": True
            }
            response = self.client.post(self.url, data=json.dumps(dades), content_type='application/json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('any_inici', response.json()['errors'])
            self.assertIn('futur', response.json()['errors']['any_inici'][0].lower())

    #  Validació anys (any_fi anterior a any_inici)
    def test_registre_any_fi_anterior_any_inici(self):
            any_inici = now().year - 1
            any_fi = any_inici - 1
            dades = {
                "email": "erroranys@student.com",
                "password1": "ContrasenyaSegura123",
                "password2": "ContrasenyaSegura123",
                "nom": "Error",
                "cognoms": "Anys",
                "dni": "34567890B",
                "telefon": "+34600000002",
                "cicle": str(self.cicle.id),
                "any_inici": str(any_inici),
                "any_fi": str(any_fi),  # any fi abans que any inici
                "terms": True
            }
            response = self.client.post(self.url, data=json.dumps(dades), content_type='application/json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('any_fi', response.json()['errors'])
            self.assertIn('posterior', response.json()['errors']['any_fi'][0].lower())

    # No acceptació termes
    def test_registre_no_accepta_terms(self):
            dades = {
                "email": "noterms@student.com",
                "password1": "ContrasenyaSegura123",
                "password2": "ContrasenyaSegura123",
                "nom": "No",
                "cognoms": "Terms",
                "dni": "45678901C",
                "telefon": "+34600000003",
                "cicle": str(self.cicle.id),
                "any_inici": str(now().year - 2),
                "any_fi": str(now().year),
                "terms": False  # No accepta termes
            }
            response = self.client.post(self.url, data=json.dumps(dades), content_type='application/json')
            self.assertEqual(response.status_code, 400)
            self.assertIn('terms', response.json()['errors'])

    def test_registre_auditoria_en_registre_estudiant(self):
        dades = {
            "email": "test@student.com",
            "password1": "ContrasenyaSegura123",
            "password2": "ContrasenyaSegura123",
            "nom": "Test",
            "cognoms": "Estudiant",
            "dni": "12345678Z",
            "telefon": "+34600000000",
            "cicle": str(self.cicle.id),
            "any_inici": str(now().year - 2),
            "any_fi": str(now().year),
            "terms": True
        }

        response = self.client.post(self.url, data=json.dumps(dades), content_type='application/json')

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Usuari.objects.filter(email="test@student.com").exists())

        usuari = Usuari.objects.get(email="test@student.com")
        registres = RegistreAuditoria.objects.filter(usuari=usuari, accio="Alta Estudiant")

        self.assertEqual(registres.count(), 1)

        registre = registres.first()
        self.assertEqual(registre.usuari, usuari)
        self.assertEqual(registre.accio, "Alta Estudiant")
       



   

class RegistreEmpresaTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('registre_empresa_api') 
        self.sector = Sector.objects.create(nom='Tecnologia')  # Simula un sector vàlid

    def test_registre_empresa_ok(self):
        data = {
            'email': 'empresa@test.com',
            'password1': 'ContrasenyaSegura123',
            'password2': 'ContrasenyaSegura123',
            'nom': 'Anna',
            'cognoms': 'Serra',
            'cif': 'B12345678',
            'nom_comercial': 'TechPro',
            'rao_social': 'Tech Professionals S.A.',
            'sector': self.sector.id,
            'telefon': '+34666777888',
            'terms': 'on'
        }
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['success'])
        self.assertEqual(Empresa.objects.count(), 1)

    def test_error_json_mal_format(self):
        response = self.client.post(
            self.url,
            data="{email: 'malament'}",  # JSON no vàlid
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('message', response.json())

    def test_email_duplicat(self):
        

        Usuari.objects.create_user(email='empresa@test.com', password='1234')
        data = {
            'email': 'empresa@test.com',
            'password1': 'ContrasenyaSegura123',
            'password2': 'ContrasenyaSegura123',
            'nom': 'Anna',
            'cognoms': 'Serra',
            'cif': 'B12345678',
            'nom_comercial': 'TechPro',
            'rao_social': 'Tech Professionals S.A.',
            'sector': self.sector.id,
            'telefon': '+34666777888',
            'terms': 'on'
        }
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json()['errors'])

    def test_contrasenyes_no_coincideixen(self):
        data = {
            'email': 'nova@empresa.com',
            'password1': 'ABC123456',
            'password2': 'DIFERENT123',
            'nom': 'Anna',
            'cognoms': 'Serra',
            'cif': 'B12345678',
            'nom_comercial': 'TechPro',
            'rao_social': 'Tech Professionals S.A.',
            'sector': self.sector.id,
            'telefon': '+34666777888',
            'terms': 'on'
        }
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('password2', response.json()['errors'])

    def test_cif_format_invalid(self):
        data = {
            'email': 'nova@empresa.com',
            'password1': 'ABC123456',
            'password2': 'ABC123456',
            'nom': 'Anna',
            'cognoms': 'Serra',
            'cif': '123INVALID',
            'nom_comercial': 'TechPro',
            'rao_social': 'Tech Professionals S.A.',
            'sector': self.sector.id,
            'telefon': '+34666777888',
            'terms': 'on'
        }
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('cif', response.json()['errors'])

    def test_falta_termes_condicions(self):
        data = {
            'email': 'nova@empresa.com',
            'password1': 'ABC123456',
            'password2': 'ABC123456',
            'nom': 'Anna',
            'cognoms': 'Serra',
            'cif': 'B12345678',
            'nom_comercial': 'TechPro',
            'rao_social': 'Tech Professionals S.A.',
            'sector': self.sector.id,
            'telefon': '+34666777888',
            'terms': ''  # No acceptat
        }
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('terms', response.json()['errors'])

    def test_crea_registre_auditoria_despres_registre_empresa(self):
        payload = {
            "email": "empresa5@example.com",
            "password1": "ContrasenyaSegura123!",
            "password2": "ContrasenyaSegura123!",
            "nom": "Clara",
            "cognoms": "Martí",
            "cif": "B11111222",
            "nom_comercial": "AuditTech",
            "rao_social": "AuditTech SL",
            "sector": self.sector.id,
            "telefon": "+34666000000",
            "terms": "true"
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 201)
        usuari = Usuari.objects.get(email="empresa5@example.com")
        registres = RegistreAuditoria.objects.filter(usuari=usuari, accio="Alta Empresa")
        self.assertEqual(registres.count(), 1)

        registre = registres.first()
        self.assertEqual(registre.usuari, usuari)
        self.assertEqual(registre.accio, "Alta Empresa")
      

