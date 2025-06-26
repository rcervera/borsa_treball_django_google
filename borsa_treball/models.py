from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.exceptions import ValidationError 
from django.utils import timezone
from datetime import datetime
import os
import time  
import uuid

class UsuariManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('L\'email és obligatori')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class Usuari(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    nom = models.CharField(max_length=255, blank=True)
    cognoms = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    TIPUS_USUARI = [
        ('ADM', 'Administrador'),
        ('RES', 'Responsable Borsa'),
        ('EST', 'Estudiant'),
        ('EMP', 'Empresa'),
    ]
    
    tipus = models.CharField(max_length=3, choices=TIPUS_USUARI, default='EST')
    telefon = models.CharField(max_length=15, blank=True, null=True)
    data_naixement = models.DateField(blank=True, null=True)
    adreca = models.TextField(blank=True, null=True)
    data_registre = models.DateTimeField(auto_now_add=True)
    darrera_connexio = models.DateTimeField(blank=True, null=True)
   

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UsuariManager()

    def get_full_name(self):
        return f"{self.nom} {self.cognoms}".strip()
    
    def __str__(self):
        return self.email


class Sector(models.Model):
    nom = models.CharField(max_length=100)
    
    def __str__(self):
        return self.nom



class Empresa(models.Model):
    usuari = models.OneToOneField(Usuari, on_delete=models.CASCADE, primary_key=True)
    cif = models.CharField(max_length=9, unique=True)
    nom_comercial = models.CharField(max_length=150)
    rao_social = models.CharField(max_length=150)
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True)
    descripcio = models.TextField(blank=True, null=True)
    num_treballadors = models.IntegerField(blank=True, null=True)
    web = models.URLField(blank=True, null=True)
    telefon = models.CharField(max_length=15, blank=True, null=True)
    email_contacte = models.EmailField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "empreses"
    
    def __str__(self):
        return f"Empresa: {self.nom_comercial} ({self.cif})"
    def clean(self):
        if self.usuari.tipus != 'EMP':
            raise ValidationError("Només es poden assignar usuaris amb tipus 'EMP' com a empresa.")

    

class FamiliaProfessional(models.Model):
    codi = models.CharField(max_length=5, unique=True)
    nom = models.CharField(max_length=100)
    
    class Meta:
        verbose_name_plural = "Famílies Professionals"

    def __str__(self):
        return f"{self.codi} - {self.nom}"


class Estudiant(models.Model):
    usuari = models.OneToOneField(Usuari, on_delete=models.CASCADE, primary_key=True)
    dni = models.CharField(max_length=9, unique=True)  
    carnet_conduir = models.BooleanField(default=False)
           
    def clean(self):
        if self.usuari.tipus != 'EST':
            raise ValidationError("Només es poden assignar usuaris amb tipus 'EST' com a estudiant.")

    def __str__(self):
        return f"Estudiant: {self.usuari.get_full_name()}"
    
    
    

class Cicle(models.Model):
    familia = models.ForeignKey(FamiliaProfessional, on_delete=models.CASCADE)
    codi = models.CharField(max_length=10)
    nom = models.CharField(max_length=150)
    NIVELLS = [
        ('GM', 'Grau Mitjà'),
        ('GS', 'Grau Superior'),
        ('ESP', 'Especialització'),
    ]
    grau = models.CharField(max_length=3, choices=NIVELLS)
    durada = models.IntegerField()  # En hores o mesos
    
    class Meta:
        unique_together = ('familia', 'codi')
    
    def __str__(self):
        return f"{self.codi} - {self.nom} ({self.grau})"




    

class EstudiEstudiant(models.Model):
   
    estudiant = models.ForeignKey(
        Estudiant, 
        on_delete=models.CASCADE, 
        related_name='estudis'
    )
    cicle = models.ForeignKey(
        Cicle, 
        on_delete=models.CASCADE,
        related_name='estudiants_matriculats'
    )
    any_inici = models.IntegerField(
        verbose_name="Any d'inici",
        help_text="Any en què va començar aquest cicle"
    )
    any_fi = models.IntegerField(
        verbose_name="Any de finalització",
        help_text="Any en què va finalitzar o preveu finalitzar",
        null=True,
        blank=True
    )
    centre_estudis = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Centre d'estudis",
        help_text="Nom del centre on es cursa/va cursar"
    )
    
    data_creacio = models.DateTimeField(auto_now_add=True)
    data_modificacio = models.DateTimeField(auto_now=True)

    
    class Meta:
        verbose_name = "Estudi estudiant"
        verbose_name_plural = "Estudis estudiant"
        unique_together = ('estudiant', 'cicle', 'any_inici')  # Evita duplicats
        ordering = ['-any_inici']
    
    def __str__(self):
        return f"{self.estudiant.usuari.get_full_name()} - {self.cicle.nom} ({self.any_inici}-{self.any_fi or 'actualitat'})"
    
    
    def clean(self):    
        
        # Validar que any_fi sigui posterior a any_inici
        if self.any_fi and self.any_fi <= self.any_inici:
            raise ValidationError("L'any de finalització ha de ser posterior a l'any d'inici")
        
        # Validar que any_inici no sigui futur
        if self.any_inici > datetime.now().year:
            raise ValidationError("L'any d'inici no pot ser futur")
        
       



class CapacitatClau(models.Model):
    """Capacitats o competències predefinides que es poden requerir en una oferta"""
    nom = models.CharField(max_length=100, unique=True)
    descripcio = models.TextField(blank=True)
    categoria = models.CharField(max_length=50, blank=True)  
    
    def __str__(self):
        return self.nom
    class Meta:
        verbose_name = "Capacitat Clau"
        verbose_name_plural = "Capacitats Clau"


class CapacitatOferta(models.Model):
    oferta = models.ForeignKey('Oferta', on_delete=models.CASCADE, related_name='capacitats')
    nom = models.CharField(max_length=100, help_text="Nom de la capacitat clau (lliure o suggerida)")
  
    class Meta:       
        verbose_name = "Capacitat clau de l'oferta"
        verbose_name_plural = "Capacitats clau de l'oferta"

    def __str__(self):
        return f"Capacitat {self.nom}"


class Funcio(models.Model):
    """Funció específica requerida en una oferta (text lliure)"""
    oferta = models.ForeignKey('Oferta', on_delete=models.CASCADE, related_name='funcions')
    descripcio = models.TextField()
    ordre = models.PositiveSmallIntegerField(default=1)  # Per ordenar funcions
    
    class Meta:
        ordering = ['ordre']
        verbose_name = "Funció"
        verbose_name_plural = "Funcions"
    
    def __str__(self):
        return f"Funció {self.ordre} - {self.descripcio[:50]}..."


class NivellIdioma(models.Model):
    oferta = models.ForeignKey('Oferta', on_delete=models.CASCADE, related_name='idiomes')
    idioma = models.CharField(max_length=100, blank=True, help_text="Ex: anglès, català...")
    nivell = models.CharField(max_length=100, blank=True, help_text="Ex: alt, mitjà, nadiu...")

    class Meta:
        verbose_name = "Nivell d'idioma"
        verbose_name_plural = "Nivells d'idioma"

    def __str__(self):
        return f"{self.idioma or '-'} ({self.nivell or '-'})"
    

class EstatOferta(models.TextChoices):
    OCULT = 'OC', 'Oculta'  # No és visible per estudiants
    REVISIO = 'RV', 'En revisió'  # L'empresa l'ha creada, però està pendent d'activació
    ACTIU = 'AC', 'Activa'  # Publicada pel responsable de la borsa i visible
    TANCAT = 'TC', 'Tancada'  # Vacant coberta o oferta finalitzada



class Oferta(models.Model):
    TIPUS_CONTRACTE = [
        ('PR', 'Pràctiques'),
        ('TC', 'Contracte en pràctiques'),
        ('TI', 'Contracte temporal'),
        ('IN', 'Contracte indefinit'),       
    ]

    JORNADA = [
        ('CO', 'Completa'),
        ('PA', 'Parcial'),
        ('FL', 'Flexible'),
    ]

    PUBLIC_DESTINATARI = [
        ('EST', 'Estudiant'),
        ('TIT', 'Titulat/da'),
        ('AMB', 'Estudiant i Titulat/da'),
    ]

    EXPERIENCIA  = [
        ('SE', 'Sense experiència'),
        ('2A', '> 2 anys'),
        ('5A', '> 5 anys'),
    ]

    estat = models.CharField(
        max_length=2, 
        choices=EstatOferta.choices,
        default=EstatOferta.REVISIO,
        verbose_name="Estat de l'oferta",
        help_text="Controla la visibilitat i disponibilitat de l'oferta"
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='ofertes')
    
    # informació bàsica
    # camp obligatoris
    titol = models.CharField(max_length=100)
    descripcio = models.TextField()
    numero_vacants = models.PositiveSmallIntegerField(default=1, verbose_name="Número vacants")
    data_limit = models.DateField()
    lloc_treball = models.CharField(max_length=100)


    tipus_contracte = models.CharField(max_length=2, choices=TIPUS_CONTRACTE)
    jornada = models.CharField(max_length=2, choices=JORNADA)
    hores_setmanals = models.PositiveSmallIntegerField(blank=True,null=True,verbose_name="Hores setmanals", help_text="Només s'utilitza si la jornada és parcial")
    horari = models.CharField(max_length=100,blank=True,null=True)
    public_destinatari = models.CharField(max_length=3,blank=True,null=True, choices=PUBLIC_DESTINATARI,default='AMB', verbose_name="A qui va dirigida")
    experiencia = models.CharField(max_length=2,choices=EXPERIENCIA,blank=True,null=True,verbose_name="Experiència requerida")
    salari = models.CharField(max_length=50, blank=True, null=True)

    cicles = models.ManyToManyField(Cicle, related_name='ofertes')
    capacitats_clau = models.ManyToManyField(CapacitatClau, blank=True, related_name='ofertes')

    data_publicacio = models.DateField(auto_now_add=True)
        
    
    # altres requesits que es vulguin posar
    requisits = models.TextField(blank=True, null=True)    
    # Camps optatius, de moment no es fan servir
    contacte_nom = models.CharField(max_length=100, blank=True,null=True)
    contacte_email = models.EmailField(blank=True,null=True)
    contacte_telefon = models.CharField(max_length=15, blank=True,null=True)

   
    # Visible per l'empresa
    visible = models.BooleanField(default=True, help_text="Controlat per l'empresa")
    # Activació per part del responsable de borsa
    activa = models.BooleanField(default=False, help_text="Activat pel responsable de la borsa de treball")

    tancada = models.BooleanField(default=False, verbose_name="Oferta tancada", help_text="Indica si l'oferta ha estat tancada (ja s'ha cobert la vacant, etc.)")
    valoracio_empresa = models.TextField(blank=True, null=True, verbose_name="Valoració de l'Empresa", help_text="La valoració de l'empresa sobre el procés o els candidats.")
    valoracio_responsable = models.TextField(blank=True, null=True, verbose_name="Valoració del Responsable", help_text="La valoració del responsable de la borsa de treball sobre el procés.")
  
    @property
    def es_caducada(self):
        if self.data_limit:
            return self.data_limit < timezone.now().date()
        return False  # o True si vols considerar-la caducada per defecte

    def __str__(self):
        return f"{self.titol}"
    

    class Meta:
        verbose_name = "Oferta"
        verbose_name_plural = "Ofertes"
        ordering = ['-data_publicacio']



class EstatCandidatura(models.TextChoices):
    REBUTJADA = 'RJ', 'Rebutjada'
    EN_PROCES = 'EP', 'En procés'
    PRESELECCIONADA = 'PR', 'Preseleccionada'
    ENTREVISTA = 'EN', 'Entrevista programada'
    CONTRATADA = 'CO', 'Contractada'

def candidatura_cv_upload_to(instance, filename):
    return f'private/candidatures/{instance.estudiant.id}/{filename}'


def curriculum_upload_path(instance, filename):
    """
    Genera una ruta única y organizada para cada currículum
    Formato: curriculaums/YYYY/MM/uuid.ext
    """
    ext = os.path.splitext(filename)[1].lower()  # Normaliza extensión a minúsculas
    unique_id = uuid.uuid4()  # Genera un UUID único
    return os.path.join(
        'curriculums',
        time.strftime("%Y"),
        time.strftime("%m"),
        f"{unique_id}{ext}"
    )

class Candidatura(models.Model):
    oferta = models.ForeignKey(
        Oferta,
        on_delete=models.CASCADE,
        related_name='candidatures',
        verbose_name='Oferta'
    )
    estudiant = models.ForeignKey(
        Estudiant,
        on_delete=models.CASCADE,
        related_name='candidatures',
        verbose_name='Estudiant'
    )
    data_candidatura = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data de candidatura'
    )
    estat = models.CharField(
        max_length=2,
        choices=EstatCandidatura.choices,
        default=EstatCandidatura.EN_PROCES,
        verbose_name='Estat'
    )
    carta_presentacio = models.TextField(
        blank=True,
        null=True,
        verbose_name='Carta de presentació'
    )
    cv_adjunt = models.FileField(
        upload_to=curriculum_upload_path,
        blank=True,
        null=True,
        verbose_name='CV adjunt'
    )
    altres_adjunts = models.FileField(
        upload_to='private/candidatures/adjunts/',
        blank=True,
        null=True,
        verbose_name='Altres documents'
    )
    data_canvi_estat = models.DateTimeField(
        auto_now=True,
        verbose_name='Últim canvi d\'estat'
    )
    notes_empresa = models.TextField(
        blank=True,
        null=True,
        verbose_name='Notes internes de l\'empresa'
    )
    puntuacio = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name='Puntuació (0-100)',
        help_text='Puntuació assignada per l\'empresa'
    )

    # Activació per part del responsable de borsa
    activa = models.BooleanField(default=False, help_text="Activat pel responsable de la borsa de treball")


    class Meta:
        verbose_name = 'Candidatura'
        verbose_name_plural = 'Candidatures'
        unique_together = ('oferta', 'estudiant')  # Evita candidatures duplicades
        ordering = ['-data_candidatura']

    def __str__(self):
        return f"Candidatura de {self.estudiant} a {self.oferta}"

    @property
    def temps_des_candidatura(self):
        """Retorna el temps transcorregut des de la candidatura"""
        from django.utils import timezone
        return timezone.now() - self.data_candidatura
    


class Noticia(models.Model):
    DESTINATARIS = [
        ('TOTHOM', 'Tothom'),
        ('ESTUDIANTS', 'Estudiants'),
        ('EMPRESES', 'Empreses'),
    ]

    titol = models.CharField(max_length=200)
    descripcio = models.TextField()
    cos = models.TextField()
    url = models.URLField(blank=True, null=True)
    imatge = models.ImageField(upload_to='noticies/imatges/', blank=True, null=True)
    document = models.FileField(upload_to='noticies/documents/', blank=True, null=True)
    destinatari = models.CharField(max_length=10, choices=DESTINATARIS, default='TOTHOM')
    data_publicacio = models.DateTimeField(default=timezone.now)
    visible = models.BooleanField(default=True)

    def __str__(self):
        return self.titol
    
    class Meta:
        verbose_name = "Notícia"
        verbose_name_plural = "Notícies"
        ordering = ['-data_publicacio']



class RegistreAuditoria(models.Model):
    accio = models.CharField(max_length=50)  # Ex: "Alta Oferta", "Modificació Estudiant", etc.
    model_afectat = models.CharField(max_length=100)
   # objecte_id = models.PositiveIntegerField(null=True, blank=True)
    descripcio = models.TextField()
    usuari = models.ForeignKey(Usuari, on_delete=models.SET_NULL, null=True, blank=True)
    data = models.DateTimeField(default=timezone.now)
    revisat = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.accio} per {self.usuari or 'Anònim'} - {self.data.strftime('%Y-%m-%d %H:%M:%S')}"

    class Meta:
        verbose_name = "Registre d'auditoria"
        verbose_name_plural = "Registres d'auditoria"
        ordering = ['-data']



class Missatge(models.Model):
    remitent = models.ForeignKey(
        Usuari,
        related_name='missatges_enviats',
        on_delete=models.CASCADE
    )
    destinatari = models.ForeignKey(
        Usuari,
        related_name='missatges_rebuts',
        on_delete=models.CASCADE
    )
    assumpte = models.CharField(max_length=255)
    contingut = models.TextField()
    llegit = models.BooleanField(default=False)
    creat_el = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"De {self.remitent.username} a {self.destinatari.username}: {self.assumpte}"
