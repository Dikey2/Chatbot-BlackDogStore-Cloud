from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("El correo es obligatorio.")
        user = self.model(email=email.strip().lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True, role="admin")
        return self._create(email, password, **extra)


class User(AbstractUser):
    """Usuario del sistema con rol (RF-08). Inicia sesión con su correo."""

    class Role(models.TextChoices):
        CLIENTE = "cliente", "Cliente"
        ASESOR = "asesor", "Asesor"
        ADMIN = "admin", "Administrador"

    username = None
    first_name = None
    last_name = None
    name = models.CharField("nombre", max_length=150)
    email = models.EmailField("correo", unique=True)
    role = models.CharField("rol", max_length=10, choices=Role.choices, default=Role.CLIENTE)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name
