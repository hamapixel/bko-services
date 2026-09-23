from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, password=None, **extra_fields):
        if not phone or not phone.strip():
            raise ValueError("Un numéro de téléphone est obligatoire.")
        user = self.model(phone=phone.strip(), **extra_fields)
        if user.email:
            user.email = self.normalize_email(user.email)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", self.model.Role.SUPERADMIN)

        if extra_fields["is_staff"] is not True:
            raise ValueError("Un superutilisateur doit avoir is_staff=True.")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("Un superutilisateur doit avoir is_superuser=True.")
        if extra_fields["role"] != self.model.Role.SUPERADMIN:
            raise ValueError("Un superutilisateur doit avoir le rôle SUPERADMIN.")
        return self.create_user(phone, password, **extra_fields)
