from rest_framework import serializers

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "sender", "content", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "user", "user_name", "status", "created_at"]


class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ["messages"]


class AdvisorReplySerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)


class SendMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=500)
    conversation_id = serializers.IntegerField(required=False, min_value=1)
