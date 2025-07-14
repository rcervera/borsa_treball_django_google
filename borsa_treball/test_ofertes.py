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
            usuari=self.user_empresa,
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
        self.url = reverse('afegir_oferta_api')

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
        self.assertEqual(errors.get('numero_vacants'), "Cal indicar un nombre de vacants positiu.")
        self.assertEqual(errors.get('cicles'), "Has de seleccionar almenys un cicle.")

        # 4. Assegurar que l'oferta NO s'ha creat a la base de dades
        self.assertEqual(Oferta.objects.count(), 0)

        
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

    def test_creacio_correcta_de_capacitats_funcions_i_idiomes(self):
        """
        Verifica que les capacitats, funcions i idiomes es desen correctament
        a la base de dades i estan associats a la nova oferta.
        """
        # 1. Iniciar sessió i enviar les dades
        self.client.login(email='empresa@test.com', password='password123')
        
        # self.valid_data ja conté dades per a aquests camps
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )

        # 2. Comprovar que la petició ha estat un èxit
        self.assertEqual(response.status_code, 200, "La petició hauria de ser exitosa")
        self.assertTrue(Oferta.objects.exists(), "S'hauria d'haver creat una oferta")
        
        # Obtenim l'oferta que acabem de crear
        oferta = Oferta.objects.first()

        # 3. Comprovar les Capacitats Clau (capacitatsLliures) 
        self.assertEqual(oferta.capacitats.count(), 2, "S'haurien d'haver creat 2 capacitats")
        
        # Obtenim els noms de les capacitats guardades
        noms_capacitats_desades = set(oferta.capacitats.values_list('nom', flat=True))
        noms_capacitats_esperades = set(self.valid_data['capacitatsLliures'])
        
        self.assertEqual(noms_capacitats_desades, noms_capacitats_esperades, "Els noms de les capacitats no coincideixen")

        # 4. Comprovar les Funcions i el seu ordre 
        self.assertEqual(oferta.funcions.count(), 2, "S'haurien d'haver creat 2 funcions")
        
        # Obtenim les funcions ordenades per l'atribut 'ordre'
        funcions_desades = oferta.funcions.all() # El model ja té ordering = ['ordre']
        
        # Comprovar la primera funció
        self.assertEqual(funcions_desades[0].descripcio, self.valid_data['funcions'][0])
        self.assertEqual(funcions_desades[0].ordre, 1, "L'ordre de la primera funció hauria de ser 1")
        
        # Comprovar la segona funció
        self.assertEqual(funcions_desades[1].descripcio, self.valid_data['funcions'][1])
        self.assertEqual(funcions_desades[1].ordre, 2, "L'ordre de la segona funció hauria de ser 2")

        # 5. Comprovar els Idiomes i els seus nivells 
        self.assertEqual(oferta.idiomes.count(), 2, "S'haurien d'haver creat 2 nivells d'idioma")
        
        # Obtenim els idiomes guardats com a tuples (idioma, nivell)
        idiomes_desats = set(oferta.idiomes.values_list('idioma', 'nivell'))
        
        # Creem el conjunt esperat a partir de les dades enviades
        idiomes_esperats = set(
            (item['idioma'], item['nivell']) for item in self.valid_data['idiomes']
        )
        
        self.assertEqual(idiomes_desats, idiomes_esperats, "Els idiomes i nivells desats no coincideixen")

    def test_error_jornada_parcial_quan_falten_les_hores(self):
        """
        Verifica que es retorna un error si la jornada és parcial i no s'indiquen les hores.
        """
        self.client.login(email='empresa@test.com', password='password123')
        
        # Preparem les dades: jornada parcial sense camp 'hores'
        data = self.valid_data.copy()
        data['jornada'] = 'PA'
        data.pop('hores', None) # Ens assegurem que el camp 'hores' no existeix

        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')

        # Comprovacions
        self.assertEqual(response.status_code, 400)
        errors = response.json().get('errors', {})
        self.assertEqual(errors.get('hores'), "Cal indicar un nombre d'hores positiu si la jornada és parcial.")
        self.assertEqual(Oferta.objects.count(), 0)

# ---

    def test_error_jornada_parcial_amb_hores_no_positives(self):
        """
        Verifica l'error si la jornada és parcial i les hores són zero o negatives.
        """
        self.client.login(email='empresa@test.com', password='password123')
        
        # Preparem les dades: jornada parcial amb hores a zero
        data = self.valid_data.copy()
        data['jornada'] = 'PA'
        data['hores'] = 0

        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')

        # Comprovacions
        self.assertEqual(response.status_code, 400)
        errors = response.json().get('errors', {})
        self.assertEqual(errors.get('hores'), "Cal indicar un nombre d'hores positiu si la jornada és parcial.")
        self.assertEqual(Oferta.objects.count(), 0)

# ---

    def test_error_jornada_parcial_amb_hores_no_numeriques(self):
        """
        Verifica l'error si la jornada és parcial i les hores no són un número.
        """
        self.client.login(email='empresa@test.com', password='password123')
        
        # Preparem les dades: jornada parcial amb hores com a text
        data = self.valid_data.copy()
        data['jornada'] = 'PA'
        data['hores'] = 'vint' # Valor no numèric

        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')

        # Comprovacions
        self.assertEqual(response.status_code, 400)
        errors = response.json().get('errors', {})
        self.assertEqual(errors.get('hores'), "Cal indicar un nombre d'hores positiu si la jornada és parcial.")
        self.assertEqual(Oferta.objects.count(), 0)

# ---

    def test_exit_jornada_parcial_amb_hores_correctes(self):
        """
        Verifica que l'oferta es crea correctament amb jornada parcial i hores vàlides.
        """
        self.client.login(email='empresa@test.com', password='password123')

        # Preparem les dades: jornada parcial amb hores correctes
        data = self.valid_data.copy()
        data['jornada'] = 'PA'
        data['hores'] = 20

        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')
        
        # Comprovacions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Oferta.objects.count(), 1)
        
        oferta_creada = Oferta.objects.first()
        self.assertEqual(oferta_creada.jornada, 'PA')
        self.assertEqual(oferta_creada.hores_setmanals, 20)

    
    def test_text_llarg_en_charfields_es_retalla_correctament(self):
        """
        Verifica que si s'envia text més llarg del permès per a un CharField,
        aquest es retalla a la mida màxima del model en lloc de donar error.
        """
        self.client.login(email='empresa@test.com', password='password123')

        # 1. Preparem textos més llargs que els límits dels camps del model
        # titol (max=200), salari (max=250)
        text_llarg_titol = "A" * 250
        text_llarg_salari = "S" * 300
        text_llarg_lloc_treball = "B" * 200  # Més llarg que el permès
        text_llarg_horari = "H" * 300

        # 2. Modifiquem les dades vàlides amb els textos llargs
        data = self.valid_data.copy()
        data['titol'] = text_llarg_titol
        data['salari'] = text_llarg_salari
        data['lloc_treball'] = text_llarg_lloc_treball
        data['horari'] = text_llarg_horari 

        # 3. Realitzem la petició
        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')

        # 4. Comprovem que la petició ha tingut èxit (codi 200)
        self.assertEqual(response.status_code, 200, "La petició hauria de ser exitosa, no hauria de fallar per text llarg")
        self.assertEqual(Oferta.objects.count(), 1, "S'hauria d'haver creat una oferta")
        
        # 5. Obtenim l'objecte creat i verifiquem que les dades s'han retallat
        oferta_creada = Oferta.objects.first()

        # Comprovació del títol (esperem 100 caràcters)
        self.assertEqual(len(oferta_creada.titol), 200)
        self.assertEqual(oferta_creada.titol, "A" * 200)

        # Comprovació del salari (esperem 50 caràcters)
        self.assertEqual(len(oferta_creada.salari), 250)
        self.assertEqual(oferta_creada.salari, "S" * 250)

        # Comprovació del lloc de treball (esperem 100 caràcters)
        self.assertEqual(len(oferta_creada.lloc_treball), 100)  
        self.assertEqual(oferta_creada.lloc_treball, "B" * 100)

        # Comprovació de l'horari (esperem 250 caràcters)
        self.assertEqual(len(oferta_creada.horari), 250)    
        self.assertEqual(oferta_creada.horari, "H" * 250)


class ActualitzarOfertaAPITestCase(TestCase):

    def setUp(self):
        """
        Prepara un entorn de prova amb usuari empresa, una oferta i cicles associats.
        """
        self.client = Client()

        self.user = Usuari.objects.create_user(
            email='empresa@test.com',
            password='password123',
            tipus='EMP'
        )
        self.empresa = Empresa.objects.create(
            usuari=self.user,
            nom_comercial="Empresa Prova",
            cif="B12345678"
        )

        self.familia = FamiliaProfessional.objects.create(codi="IFC", nom="Informàtica")
        self.cicle = Cicle.objects.create(
            familia=self.familia,
            codi="DAW",
            nom="Desenvolupament Web",
            grau="GS",
            durada=2000
        )

        self.oferta = Oferta.objects.create(
            empresa=self.empresa,
            titol="Oferta inicial",
            descripcio="Descripció inicial",
            data_limit=timezone.now().date() + datetime.timedelta(days=10),
            tipus_contracte="PR",
            jornada="CO",
            lloc_treball="Barcelona",
            numero_vacants=1,
            estat='RV'
        )
        self.oferta.cicles.add(self.cicle)

        self.url = reverse('api_actualitzar_oferta', args=[self.oferta.id])

        self.dades_actualitzades = {
            "titol": "Oferta actualitzada",
            "descripcio": "Nova descripció.",
            "data_limit": (timezone.now().date() + datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
            "tipus_contracte": "IN",
            "jornada": "PA",
            "hores": 25,
            "lloc_treball": "Girona",
            "numero_vacants": 3,
            "cicles": [self.cicle.id],
            "destinatari": "EST",
            "experiencia": "SE",
            "requisits": "Coneixements de Python.",
            "horari": "Matins",
            "salari": "20000€/any",
            "capacitatsLliures": ["Comunicació", "Adaptabilitat"],
            "funcions": ["Desenvolupament web", "Gestió de base de dades"],
            "idiomes": [
                {"idioma": "Anglès", "nivell": "mig"},
                {"idioma": "Català", "nivell": "alt"}
            ]
        }

    def test_actualitzar_oferta_correctament(self):
        """
        Verifica que una oferta es pot actualitzar correctament amb dades vàlides.
        """
        self.client.login(email='empresa@test.com', password='password123')

        response = self.client.put(
            self.url,
            data=json.dumps(self.dades_actualitzades),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        self.oferta.refresh_from_db()
        self.assertEqual(self.oferta.titol, self.dades_actualitzades['titol'])
        self.assertEqual(self.oferta.jornada, 'PA')
        self.assertEqual(self.oferta.hores_setmanals, 25)
        self.assertEqual(self.oferta.numero_vacants, 3)
        self.assertEqual(self.oferta.capacitats.count(), 2)
        self.assertEqual(self.oferta.funcions.count(), 2)
        self.assertEqual(self.oferta.idiomes.count(), 2)

    def test_error_si_no_autenticat(self):
        """
        Verifica que un usuari no autenticat no pot actualitzar una oferta.
        """
        response = self.client.put(self.url, data=json.dumps(self.dades_actualitzades), content_type='application/json')
        self.assertEqual(response.status_code, 302)  # redirecció a login

    def test_error_si_jornada_parcial_sense_hores(self):
        """
        Verifica que es retorna un error si la jornada és parcial i no s'especifica el nombre d'hores.
        """
        self.client.login(email='empresa@test.com', password='password123')
        data = self.dades_actualitzades.copy()
        data.pop('hores')

        response = self.client.put(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('hores', response.json()['errors'])

    def test_error_si_titol_buit(self):
        """
        Verifica que es retorna un error si el títol és buit.
        """
        self.client.login(email='empresa@test.com', password='password123')
        data = self.dades_actualitzades.copy()
        data['titol'] = ""

        response = self.client.put(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('titol', response.json()['errors'])

    def test_actualitzacio_retalla_camps_llargs(self):
        """
        Verifica que els camps de text massa llargs són retallats a la mida permesa pel model.
        """
        self.client.login(email='empresa@test.com', password='password123')
        data = self.dades_actualitzades.copy()
        data['titol'] = "X" * 300  # límit 200
        data['salari'] = "S" * 300  # límit 250
        data['lloc_treball'] = "L" * 200  # límit 100
        data['horari'] = "H" * 300  # límit 250

        response = self.client.put(self.url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, 200)

        self.oferta.refresh_from_db()
        self.assertEqual(len(self.oferta.titol), 200)
        self.assertEqual(len(self.oferta.salari), 250)
        self.assertEqual(len(self.oferta.lloc_treball), 100)
        self.assertEqual(len(self.oferta.horari), 250)

def test_actualitzar_funcions_capacitats_idiomes_i_cicles(self):
    """
    Verifica que les funcions, capacitats, idiomes i cicles es substitueixen correctament
    durant l'actualització de l'oferta.
    """
    self.client.login(email='empresa@test.com', password='password123')

    # Cicle i relacions inicials (abans de l’actualització)
    self.oferta.funcions.create(descripcio="Funció antiga", ordre=1)
    CapacitatOferta.objects.create(oferta=self.oferta, nom="Capacitat antiga")
    NivellIdioma.objects.create(oferta=self.oferta, idioma="Francès", nivell="baix")

    # Afegim un altre cicle
    cicle_nou = Cicle.objects.create(
        familia=self.familia,
        codi="ASIX",
        nom="Administració de Sistemes",
        grau="GS",
        durada=2000
    )

    self.oferta.cicles.set([self.cicle, cicle_nou])

    # Verificació prèvia
    self.assertEqual(self.oferta.funcions.count(), 1)
    self.assertEqual(self.oferta.capacitats.count(), 1)
    self.assertEqual(self.oferta.idiomes.count(), 1)
    self.assertEqual(self.oferta.cicles.count(), 2)

    # Nous valors (substitució completa)
    dades_noves = self.dades_actualitzades.copy()
    dades_noves['funcions'] = ["Nova funció 1", "Nova funció 2"]
    dades_noves['capacitatsLliures'] = ["Organització", "Creativitat"]
    dades_noves['idiomes'] = [{"idioma": "Anglès", "nivell": "alt"}]
    dades_noves['cicles'] = [cicle_nou.id]  # només el nou

    response = self.client.put(
        self.url,
        data=json.dumps(dades_noves),
        content_type='application/json'
    )
    self.assertEqual(response.status_code, 200)
    self.assertTrue(response.json()['success'])

    self.oferta.refresh_from_db()

    # Verificacions posteriors
    self.assertEqual(self.oferta.funcions.count(), 2)
    funcions = list(self.oferta.funcions.order_by('ordre').values_list('descripcio', flat=True))
    self.assertEqual(funcions, ["Nova funció 1", "Nova funció 2"])

    self.assertEqual(self.oferta.capacitats.count(), 2)
    noms_capacitats = set(self.oferta.capacitats.values_list('nom', flat=True))
    self.assertEqual(noms_capacitats, {"Organització", "Creativitat"})

    self.assertEqual(self.oferta.idiomes.count(), 1)
    idioma = self.oferta.idiomes.first()
    self.assertEqual((idioma.idioma, idioma.nivell), ("Anglès", "alt"))

    self.assertEqual(self.oferta.cicles.count(), 1)
    self.assertEqual(self.oferta.cicles.first().id, cicle_nou.id)

def test_ordre_de_funcions_es_manté_correctament(self):
    """
    Verifica que les funcions es desen amb l'ordre correcte durant l'actualització.
    """
    self.client.login(email='empresa@test.com', password='password123')

    # Funcions inicials antigues (que seran eliminades)
    self.oferta.funcions.create(descripcio="Funció antiga 1", ordre=1)
    self.oferta.funcions.create(descripcio="Funció antiga 2", ordre=2)

    # Noves funcions a actualitzar
    noves_funcions = [
        "Analitzar requeriments",
        "Dissenyar arquitectura",
        "Implementar funcionalitats",
        "Realitzar proves",
        "Documentar el projecte"
    ]

    dades = self.dades_actualitzades.copy()
    dades['funcions'] = noves_funcions

    response = self.client.put(
        self.url,
        data=json.dumps(dades),
        content_type='application/json'
    )

    self.assertEqual(response.status_code, 200)
    self.assertTrue(response.json()['success'])

    self.oferta.refresh_from_db()
    funcions_desa = list(self.oferta.funcions.order_by('ordre'))

    # Comprovar que es guarden totes les funcions noves
    self.assertEqual(len(funcions_desa), len(noves_funcions))

    # Comprovar l'ordre de cada funció
    for i, funcio in enumerate(funcions_desa):
        self.assertEqual(funcio.ordre, i + 1)
        self.assertEqual(funcio.descripcio, noves_funcions[i])
