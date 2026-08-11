from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("db_details", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="credentialrecord",
            name="unique_credential_display_name_per_type",
        ),
        migrations.RemoveIndex(
            model_name="credentialrecord",
            name="cred_component_type_idx",
        ),
        migrations.AddField(
            model_name="credentialrecord",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="credentialrecord",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name="credentialrecord",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_deleted", False)),
                fields=("component", "credential_type", "display_name"),
                name="unique_active_credential_display_name",
            ),
        ),
        migrations.AddIndex(
            model_name="credentialrecord",
            index=models.Index(
                fields=["component", "credential_type", "is_deleted"],
                name="cred_component_active_idx",
            ),
        ),
    ]
