from rest_framework import serializers

from .models import FAQ


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = [
            "id",
            "category",
            "question",
            "answer",
            "keywords",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def validate_keywords(self, value):
        if not [k for k in value.split(",") if k.strip()]:
            raise serializers.ValidationError("Indique al menos una palabra clave.")
        return value
