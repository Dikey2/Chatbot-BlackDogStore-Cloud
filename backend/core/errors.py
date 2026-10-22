"""Formato único de errores de la API.

    {"error": {"code": "...", "message": "...", "fields": {...}}}

`fields` solo aparece en errores de validación (400).
"""
import logging

from django.http import JsonResponse
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def _body(code, message, **extra):
    return {"error": {"code": code, "message": message, **extra}}


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        # Error no previsto: se registra completo y el cliente no ve detalles internos.
        logger.exception("Error no controlado en %s", context.get("view"))
        return Response(_body("server_error", "Error interno del servidor."), status=500)

    if isinstance(exc, exceptions.ValidationError):
        response.data = _body("validation_error", "Datos inválidos.", fields=response.data)
    else:
        detail = response.data.get("detail", "") if isinstance(response.data, dict) else ""
        code = getattr(detail, "code", None) or getattr(exc, "default_code", "error")
        if response.status_code == 404:
            # El texto por defecto de Django nombra el modelo interno.
            detail = "Recurso no encontrado."
        response.data = _body(code, str(detail))
    return response


def api_not_found(request, *args, **kwargs):
    return JsonResponse(_body("not_found", "Ruta no encontrada."), status=404)
