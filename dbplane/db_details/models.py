from django.db import models
from django.db.models import Q


class CredentialRecord(models.Model):
    component = models.CharField(max_length=64)
    credential_type = models.CharField(max_length=64)
    display_name = models.CharField(max_length=128)
    public_data = models.JSONField(default=dict, blank=True)
    encrypted_secret_data = models.TextField(blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["component", "credential_type", "display_name"],
                condition=Q(is_deleted=False),
                name="unique_active_credential_display_name",
            )
        ]
        indexes = [
            models.Index(
                fields=["component", "credential_type", "is_deleted"],
                name="cred_component_active_idx",
            ),
        ]

    def __str__(self):
        return f"{self.component}:{self.credential_type}:{self.display_name}"


class ClusterDetails(models.Model):
    db_type = models.CharField(max_length=64)
    display_name = models.CharField(max_length=128)
    dc_ips = models.TextField()
    dc_ports = models.TextField()
    dc_ha_ips = models.TextField()
    dc_ha_ports = models.TextField()
    dr_ips = models.TextField()
    dr_ports = models.TextField()
    dr_ha_ips = models.TextField()
    dr_ha_ports = models.TextField()
    arbiter_ips = models.TextField(default='', blank=True)
    arbiter_ports = models.TextField(default='', blank=True)
    db_username = models.CharField(max_length=128, default='')
    db_name = models.CharField(max_length=128, default='')
    db_password = models.TextField(default='')
    auth_mechanism = models.CharField(max_length=64, default='', blank=True)
    server_username = models.CharField(max_length=128, default='')
    server_password = models.TextField(default='')
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cluster_details'

    def __str__(self):
        return f"{self.db_type}:{self.display_name}"


class DeploymentResult(models.Model):
    cluster = models.ForeignKey(ClusterDetails, on_delete=models.CASCADE, related_name='deployments')
    job_name = models.CharField(max_length=128)           # Auto: DeployJob0001, DeployJob0002
    cluster_name = models.CharField(max_length=128)        # Snapshot of cluster display_name
    status = models.CharField(max_length=32, default='running')  # running, completed, failed
    deploy_parameters = models.JSONField(default=dict)     # replicaSet, logicalSession, maxSessions, etc.
    log_output = models.TextField(default='')              # Full deployment log text
    result_html = models.TextField(default='')             # Final status table HTML
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'deployment_results'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.cluster_name} - {self.job_name} ({self.status})"
