import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


def _b64url(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


class Command(BaseCommand):
    help = "Génère une paire VAPID Web Push à copier dans le fichier .env local."

    def handle(self, *args, **options):
        private_key = ec.generate_private_key(ec.SECP256R1())
        private_der = private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_raw = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )

        self.stdout.write("Copiez ces valeurs dans votre fichier .env local :")
        self.stdout.write(f"WEB_PUSH_VAPID_PUBLIC_KEY={_b64url(public_raw)}")
        self.stdout.write(f"WEB_PUSH_VAPID_PRIVATE_KEY={_b64url(private_der)}")
        self.stdout.write("WEB_PUSH_VAPID_SUBJECT=mailto:votre-email@example.com")
