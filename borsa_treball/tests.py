from django.test import TestCase

# Create your tests here.
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Estudiant  

Usuari = get_user_model()

class ActualitzarPerfilEstudiantTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.usuari = Usuari.objects.create_user(
            username='estudiant1',
            password='contrasenyaSegura',
            email='estudiant1@example.com',
            nom='Nom',
            cognoms='Cognoms',
            telefon='+34600000000',
            tipus='EST'
        )
        self.estudiant = Estudiant.objects.create(
            usuari=self.usuari,
            dni='12345678A',
            carnet_conduir=True
        )
        self.client.login(username='estudiant1', password='contrasenyaSegura')
        self.url = reverse('api_actualitzar_perfil_estudiant')  # Canvia si uses un path diferent

    def test_actualitzar_perfil_correctament(self):
        payload = {
            'nom': 'NouNom',
            'cognoms': 'NouCognom',
            'email': 'nouemail@example.com',
            'telefon': '+34611222333',
            'dni': '87654321Z',
            'carnet_conduir': False
        }
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['nom'], 'NouNom')

        self.usuari.refresh_from_db()
        self.estudiant.refresh_from_db()
        self.assertEqual(self.usuari.nom, 'NouNom')
        self.assertEqual(self.estudiant.dni, '87654321Z')

    def test_rebutja_si_no_es_estudiant(self):
        self.usuari.tipus = 'PROF'
        self.usuari.save()

        payload = {
            'nom': 'Nom',
            'cognoms': 'Cognoms',
            'email': 'altri@example.com',
            'telefon': '+34612345678',
            'dni': '87654321X',
            'carnet_conduir': True
        }
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_dades_json_mal_format(self):
        response = self.client.post(self.url, data='no és json', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('message', response.json())

    def test_error_validacio_email_invalid(self):
        payload = {
            'nom': 'Nom',
            'cognoms': 'Cognoms',
            'email': 'format_invalid',
            'telefon': '+34611222333',
            'dni': '12345678A',
            'carnet_conduir': True
        }
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json()['errors'])

    def test_error_validacio_dni_invalid(self):
        payload = {
            'nom': 'Nom',
            'cognoms': 'Cognoms',
            'email': 'valid@example.com',
            'telefon': '+34611222333',
            'dni': '1234XYZ',  # Invalid
            'carnet_conduir': True
        }
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('dni', response.json()['errors'])

    def test_error_telefon_invalid(self):
        payload = {
            'nom': 'Nom',
            'cognoms': 'Cognoms',
            'email': 'valid@example.com',
            'telefon': 'abcde12345',
            'dni': '87654321B',
            'carnet_conduir': True
        }
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('telefon', response.json()['errors'])

    def test_error_email_ja_existeix(self):
        usuari2 = Usuari.objects.create_user(
            username='estudiant2',
            password='contrasenyaSegura',
            email='ocupat@example.com',
            nom='X',
            cognoms='Y',
            tipus='EST'
        )
        payload = {
            'nom': 'Nom',
            'cognoms': 'Cognoms',
            'email': 'ocupat@example.com',  # Ja existeix
            'telefon': '+34611222333',
            'dni': '87654321B',
            'carnet_conduir': True
        }
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json()['errors'])

    def test_error_dni_ja_existeix(self):
        Estudiant.objects.create(
            usuari=Usuari.objects.create_user(
                username='algu',
                password='1234',
                email='algu@example.com',
                tipus='EST'
            ),
            dni='99999999Z'
        )
        payload = {
            'nom': 'Nom',
            'cognoms': 'Cognoms',
            'email': 'nouemail2@example.com',
            'telefon': '+34611222333',
            'dni': '99999999Z',
            'carnet_conduir': True
        }
        response = self.client.post(self.url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('dni', response.json()['errors'])
