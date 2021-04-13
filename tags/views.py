from rest_framework import viewsets
from tags.models import Tag
from tags.serializers import TagSerializer


class TagViewSet(viewsets.ModelViewSet):
    """
    Tag ViewSet description

    list: List all tags
    retrieve: Retrieve a tag
    update: Update a tag
    create: Create a tag
    partial_update: Patch a tag
    destroy: Soft delete a tag
    """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
