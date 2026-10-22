from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .rules import find_reply


class FAQInputSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=50)
    answer = serializers.CharField()
    keywords = serializers.ListField(child=serializers.CharField(max_length=100))


class ReplyInputSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=500)
    faqs = FAQInputSerializer(many=True, allow_empty=True)


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "service": "chatbot"})


@api_view(["POST"])
def reply(request):
    serializer = ReplyInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(find_reply(**serializer.validated_data))
