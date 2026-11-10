from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "sender", "content", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    # Cliente registrado o "Visitante #n" del widget. Nunca datos de otro negocio.
    user_name = serializers.CharField(source="client_name", read_only=True)
    channel = serializers.SerializerMethodField()
    assigned_to_name = serializers.CharField(
        source="assigned_to.name", read_only=True, default=None
    )

    class Meta:
        model = Conversation
        fields = [
            "id", "user", "user_name", "channel", "status", "assigned_to", "assigned_to_name",
            "created_at",
        ]

    def get_channel(self, obj):
        return "widget" if obj.visitor_id else "plataforma"


class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ["messages"]


class AdvisorReplySerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)


class ConversationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            Conversation.Status.ABIERTA,
            Conversation.Status.DERIVADA,
            Conversation.Status.ATENDIENDO,
        ]
    )


class SendMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=500)
    conversation_id = serializers.IntegerField(required=False, min_value=1)
