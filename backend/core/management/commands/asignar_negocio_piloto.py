"""Asigna al negocio piloto las FAQ, conversaciones y eventos que quedaron sin negocio.

Solo puede haberlos si, tras desplegar la plataforma multiempresa, se volvió un
tiempo a la versión anterior (que no conoce el campo ``business``). Es idempotente
y barato: se ejecuta en cada arranque, después de ``migrate``.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from chat.models import Conversation
from faqs.models import FAQ
from tenants.models import Business


class Command(BaseCommand):
    help = "Asigna al negocio piloto los registros sin negocio (tras un rollback)."

    def handle(self, *args, **options):
        pilot = Business.objects.filter(slug=settings.DEFAULT_BUSINESS_SLUG).first()
        if pilot is None:
            self.stdout.write("Sin negocio piloto: nada que asignar.")
            return
        faqs = FAQ.objects.filter(business__isnull=True).update(business=pilot)
        conversations = Conversation.objects.filter(business__isnull=True).update(business=pilot)
        self.stdout.write(f"Asignados al piloto: {faqs} FAQ, {conversations} conversaciones.")
