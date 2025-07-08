from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth import SESSION_KEY

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.Usuari = get_user_model()
        self.usuari = self.Usuari.objects.create_user(
            email='prova@example.com',
            password='contrasenyaSegura123'
        )
        self.login_url = reverse('login')  
        self.index_url = reverse('index')

    def test_login_correcte_redirecciona(self):
        response = self.client.post(self.login_url, {
            'email': 'prova@example.com',
            'password': 'contrasenyaSegura123',
        })

        # Comprova que redirigeix a la pàgina d'índex
        self.assertRedirects(response, self.index_url)

        # Comprova que el login ha estat correcte
        session = self.client.session
        self.assertIn('_auth_user_id', session)

    def test_login_incorrecte_email(self):
        response = self.client.post(self.login_url, {
            'email': 'incorrecte@example.com',
            'password': 'contrasenyaSegura123',
        })

        # No hauria de redirigir, hauria de retornar el template amb error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Correu electrònic o contrasenya incorrectes.')

    def test_login_incorrecte_contrasenya(self):
        response = self.client.post(self.login_url, {
            'email': 'prova@example.com',
            'password': 'contrasenyaIncorrecta',
        })

        # No hauria de redirigir, hauria de retornar el template amb error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Correu electrònic o contrasenya incorrectes.')


    def test_login_metode_get_renderitza_formulari(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')



class CanviContrasenyaAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.Usuari = get_user_model()
        self.usuari = self.Usuari.objects.create_user(
            email='prova@example.com',
            password='contrasenya_vella123'
        )
        self.login_url = reverse('login') 
        self.url = reverse('canviar_contrasenya')  



    def test_canvi_contrasenya_exit(self):
        self.client.login(email='prova@example.com', password='contrasenya_vella123')
        response = self.client.post(self.url, {
            'old_password': 'contrasenya_vella123',
            'new_password1': 'novaContrasenyaSegura456',
            'new_password2': 'novaContrasenyaSegura456',
        })
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {
            'success': True,
            'message': 'Contrasenya canviada correctament.'
        })

        # Verificar que realment ha canviat la contrasenya
        self.usuari.refresh_from_db()
        self.assertTrue(self.usuari.check_password('novaContrasenyaSegura456'))

    def test_contrasenya_antiga_incorrecta(self):
        self.client.login(email='prova@example.com', password='contrasenya_vella123')
        response = self.client.post(self.url, {
            'old_password': 'contrasenya_errònia',
            'new_password1': 'novaContrasenyaSegura456',
            'new_password2': 'novaContrasenyaSegura456',
        })
        self.assertEqual(response.status_code, 200)
        json = response.json()
        self.assertFalse(json['success'])
        self.assertIn('old_password', json['errors'])

    def test_contrasenyes_no_coincideixen(self):
        self.client.login(email='prova@example.com', password='contrasenya_vella123')
        response = self.client.post(self.url, {
            'old_password': 'contrasenya_vella123',
            'new_password1': 'novaContrasenyaSegura456',
            'new_password2': 'unaAltraContrasenya789',
        })
        self.assertEqual(response.status_code, 200)
        json = response.json()
        self.assertFalse(json['success'])
        self.assertIn('new_password2', json['errors'])

    def test_no_autenticat(self):
        response = self.client.post(self.url, {
            'old_password': 'qualsevol',
            'new_password1': 'alguna123',
            'new_password2': 'alguna123',
        })
        self.assertEqual(response.status_code, 302)  # redirecció a login
        self.assertIn('/login', response.url)
    
    def test_sessio_expirada(self):
        # Simulem una sessió expirada
        self.client.logout()
        response = self.client.post(self.url, {
            'old_password': 'contrasenya_vella123',
            'new_password1': 'novaContrasenyaSegura456',
            'new_password2': 'novaContrasenyaSegura456',
        })
        self.assertEqual(response.status_code, 302)

