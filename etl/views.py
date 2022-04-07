from rest_framework import viewsets
from etl.models import BigqueryJobs
from etl.serializers import BigqueryJobsSerializer
from rest_framework.permissions import IsAuthenticated


class BigqueryJobsViewSet(viewsets.ModelViewSet):
    """
    BigqueryJobs ViewSet description

    list: List all rows of bigquery jobs table
    retrieve: Retrieve a row from the bigquery jobs table
    update: Update a row from the bigquery jobs table
    create: Create a new row in bigquery jobs table
    partial_update: Patch a row in bigquery jobs table
    destroy: Soft delete a row of bigquery jobs table
    """

    queryset = BigqueryJobs.objects.all()
    serializer_class = BigqueryJobsSerializer
    permission_classes = [IsAuthenticated]
