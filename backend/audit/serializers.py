from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True, default=None)

    class Meta:
        model = AuditEvent
        fields = ["id", "user", "user_name", "email", "action", "result", "source", "detail", "created_at"]
        read_only_fields = fields


class PlatformAuditEventSerializer(AuditEventSerializer):
    business_name = serializers.CharField(source="business.name", read_only=True, default=None)

    class Meta(AuditEventSerializer.Meta):
        fields = AuditEventSerializer.Meta.fields + ["business", "business_name"]
        read_only_fields = fields
