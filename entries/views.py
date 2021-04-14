from rest_framework import viewsets
from entries.models import Session, SessionAnswer, Event
from entries.serializers import (
    SessionSerializer,
    SessionAnswerSerializer,
    EventSerializer,
)


class SessionViewSet(viewsets.ModelViewSet):
    """
    Session ViewSet description

    list: List all sessions
    retrieve: Retrieve a session
    update: Update a session
    create: Create a session
    partial_update: Patch a session
    destroy: Soft delete a session
    """

    serializer_class = SessionSerializer

    def get_queryset(self):
        queryset = Session.objects.filter(user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SessionAnswerViewSet(viewsets.ModelViewSet):
    """
    SessionAnswer ViewSet description

    list: List all session answers
    retrieve: Retrieve a session answer
    update: Update a session answer
    create: Create a session answer
    partial_update: Patch a session answer
    destroy: Soft delete a session answer
    """

    queryset = SessionAnswer.objects.all()
    serializer_class = SessionAnswerSerializer


class EventViewSet(viewsets.ModelViewSet):
    """
    Event ViewSet description

    list: List all events
    retrieve: Retrieve a event
    update: Update a event
    create: Create a event
    partial_update: Patch a event
    destroy: Soft delete a event
    """

    queryset = Event.objects.all()
    serializer_class = EventSerializer
