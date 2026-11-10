from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Business, BusinessDomain, ChatbotConfig, Membership, normalize_origin

User = get_user_model()


def https_or_empty(value):
    if value and not value.startswith("https://"):
        raise serializers.ValidationError("El logotipo debe ser una URL https://.")
    return value


class ChatbotConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatbotConfig
        fields = [
            "assistant_name", "welcome_message", "no_answer_message", "handoff_message",
            "handoff_keywords", "schedule", "contact_info", "primary_color", "is_active",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class BusinessSerializer(serializers.ModelSerializer):
    """Datos del negocio que su administrador puede ver y editar."""

    chatbot = ChatbotConfigSerializer(required=False)

    class Meta:
        model = Business
        fields = [
            "id", "public_id", "slug", "name", "description", "logo_url", "is_active",
            "created_at", "chatbot",
        ]
        # Un administrador de negocio no se suspende ni cambia su slug/identificador.
        read_only_fields = ["id", "public_id", "slug", "is_active", "created_at"]

    def validate_logo_url(self, value):
        return https_or_empty(value)

    def update(self, instance, validated_data):
        chatbot_data = validated_data.pop("chatbot", None)
        instance = super().update(instance, validated_data)
        if chatbot_data:
            config, _ = ChatbotConfig.objects.get_or_create(business=instance)
            for field, value in chatbot_data.items():
                setattr(config, field, value)
            config.full_clean()
            config.save()
        return instance


class PlatformBusinessSerializer(BusinessSerializer):
    """El superadministrador crea negocios y elige su slug."""

    admins = serializers.SerializerMethodField()
    counts = serializers.SerializerMethodField()

    class Meta(BusinessSerializer.Meta):
        fields = BusinessSerializer.Meta.fields + ["admins", "counts"]
        read_only_fields = ["id", "public_id", "is_active", "created_at"]

    def get_admins(self, obj):
        return [
            {"id": m.user_id, "name": m.user.name, "email": m.user.email}
            for m in obj.memberships.all()
            if m.role == Membership.Role.ADMIN
        ]

    def get_counts(self, obj):
        return {
            "faqs": getattr(obj, "faq_count", None),
            "conversations": getattr(obj, "conversation_count", None),
        }

    def create(self, validated_data):
        chatbot_data = validated_data.pop("chatbot", None) or {}
        business = Business.objects.create(**validated_data)
        ChatbotConfig.objects.create(
            business=business, **{"assistant_name": f"Asistente de {business.name}", **chatbot_data}
        )
        return business


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessDomain
        fields = ["id", "origin", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_origin(self, value):
        try:
            origin = normalize_origin(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        business = self.context["business"]
        if BusinessDomain.objects.filter(business=business, origin=origin).exists():
            raise serializers.ValidationError("Ese origen ya está autorizado.")
        return origin


class MemberSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "user", "name", "email", "role", "created_at"]
        read_only_fields = ["id", "user", "name", "email", "created_at"]


class AddMemberSerializer(serializers.Serializer):
    """Agrega a alguien al equipo. Si la cuenta no existe se crea con esta contraseña."""

    email = serializers.EmailField()
    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(
        max_length=128, required=False, allow_blank=True, write_only=True, trim_whitespace=False
    )
    role = serializers.ChoiceField(choices=Membership.Role.choices, default=Membership.Role.ASESOR)

    def validate(self, attrs):
        attrs["email"] = attrs["email"].lower()
        user = User.objects.filter(email=attrs["email"]).first()
        if user is None:
            if not attrs.get("name") or not attrs.get("password"):
                raise serializers.ValidationError(
                    {"password": ["Para una cuenta nueva indique nombre y contraseña."]}
                )
            candidate = User(name=attrs["name"], email=attrs["email"])
            try:
                validate_password(attrs["password"], user=candidate)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"password": exc.messages}) from exc
        attrs["user"] = user
        return attrs

    def save(self, business):
        data = self.validated_data
        user = data["user"]
        if user is None:
            user = User.objects.create_user(
                email=data["email"], password=data["password"], name=data["name"]
            )
        membership, created = Membership.objects.get_or_create(
            user=user, business=business, defaults={"role": data["role"]}
        )
        if not created and membership.role != data["role"]:
            membership.role = data["role"]
            membership.save(update_fields=["role"])
        return membership
