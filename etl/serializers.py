from rest_framework import serializers
from etl.models import BigqueryJobs


class BigqueryJobsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BigqueryJobs
        fields = [
            "id",
            "schema",
            "table_to_sync",
            "table_last_updated_at",
            "table_last_synced_at",
            "last_synced_row_id",
            "created_at",
            "updated_at",
        ]