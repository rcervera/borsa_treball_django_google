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

@override_settings(PRIVATE_MEDIA_ROOT=temp_dir)

class DescarregarCVCandidaturaTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(temp_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.client = Client()

        # Crear usuari estudiant
        self.user_estudiant = Usuari.objects.create_user(
            email='cv@test.com',
            password='cvpass123',
            tipus='EST',
            nom='Laura',
            cognoms='Serra'
        )
        self.estudiant = Estudiant.objects.create(
            usuari=self.user_estudiant,
            dni='88888888X'
        )

        # Crear empresa i oferta
        self.user_empresa = Usuari.objects.create_user(
            email='empresa_cv@test.com',
            password='password123',
            tipus='EMP'
        )
        self.sector = Sector.objects.create(nom='Educació')
        self.empresa = Empresa.objects.create(
            usuari=self.user_empresa,
            cif='C12345678',
            nom_comercial='Educació XXI',
            rao_social='Educació XXI SL',
            sector=self.sector
        )
        self.oferta = Oferta.objects.create(
            empresa=self.empresa,
            titol='Professor/a Tecnologia',
            descripcio='Oferta docent',
            estat='AC',
            data_limit=date(2025, 12, 31),
            lloc_treball='Girona',
            tipus_contracte='IN',
            jornada='CO'
        )

        # Crear fitxer de CV i candidatura
        self.cv_file = SimpleUploadedFile("cv.pdf", b"Contingut del CV", content_type="application/pdf")
        self.cv_file.seek(0)
        self.candidatura = Candidatura.objects.create(
            estudiant=self.estudiant,
            oferta=self.oferta,
            carta_presentacio='Carta de presentació prou extensa.jlsddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddjsldddddddddddsddddddddd',
            estat='EP',
            cv_adjunt=self.cv_file
        )

        self.url = reverse('descarregar_cv_candidatura_estudiant', args=[self.candidatura.id])

    def test_descarrega_cv_correctament(self):
        """
        Verifica que un estudiant autenticat pot descarregar el seu CV correctament.
        """
        self.client.login(email='cv@test.com', password='cvpass123')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename="CV_', response['Content-Disposition'])
        self.assertIn(b"Contingut del CV", response.content)

    def test_redirigeix_si_no_autenticat(self):
        """
        Verifica que un usuari no autenticat és redirigit a la pàgina de login.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/'))

    def test_404_si_candidatura_no_te_cv(self):
        """
        Verifica que es retorna un 404 si la candidatura no té cap CV adjunt.
        """
        self.candidatura.cv_adjunt = None
        self.candidatura.save()

        self.client.login(email='cv@test.com', password='cvpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_404_si_fitxer_eliminat_del_disc(self):
        """
        Verifica que es retorna un 404 si el fitxer CV ha estat esborrat del disc.
        """
        file_path = self.candidatura.cv_adjunt.path
        if os.path.exists(file_path):
            os.remove(file_path)

        self.assertFalse(os.path.exists(file_path))  # Confirmació

        self.client.login(email='cv@test.com', password='cvpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)



    def test_no_pot_descarregar_cv_duna_candidatura_dun_altre_estudiant(self):
        """
        Verifica que un estudiant no pot descarregar el CV d'una candidatura que no és seva.
        """
        # Nou estudiant que intentarà accedir al CV d'una altra persona
        user_estrany = Usuari.objects.create_user(
            email='altra@prova.com',
            password='altrapass',
            tipus='EST',
            nom='Pau',
            cognoms='Garcia'
        )
        Estudiant.objects.create(usuari=user_estrany, dni='77777777K')

        self.client.login(email='altra@prova.com', password='altrapass')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_usuari_sense_perfil_estudiant_redirigit(self):
        """
        Verifica que un usuari autenticat però sense perfil d'estudiant és redirigit.
        """
        user_admin = Usuari.objects.create_user(
            email='admin@prova.com',
            password='adminpass',
            tipus='ADM'
        )

        self.client.login(email='admin@prova.com', password='adminpass')
        response = self.client.get(self.url)

        # S'espera redirecció a 'index' → comprova si és un redirect 302
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse('index')))
