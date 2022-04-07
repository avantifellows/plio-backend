from django.db import models
from safedelete.models import SafeDeleteModel, HARD_DELETE

class BigqueryJobs(SafeDeleteModel):
    _safedelete_policy = HARD_DELETE

    schema = models.CharField(max_length=255, default="public")
    table_to_sync = models.CharField(max_length=255)
    table_last_updated_at = models.DateTimeField(null=True)
    table_last_synced_at = models.DateTimeField(null=True)
    last_synced_row_id = models.PositiveIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bigquery_jobs"
    
    def __str__(self):
        return "%d: %s - %s" % (self.id, self.schema, self.table_to_sync)