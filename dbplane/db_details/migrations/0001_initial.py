# Generated manually for DB Plane credential storage.

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CredentialRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("component", models.CharField(max_length=64)),
                ("credential_type", models.CharField(max_length=64)),
                ("display_name", models.CharField(max_length=128)),
                ("public_data", models.JSONField(blank=True, default=dict)),
                ("encrypted_secret_data", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="credentialrecord",
            constraint=models.UniqueConstraint(
                fields=("component", "credential_type", "display_name"),
                name="unique_credential_display_name_per_type",
            ),
        ),
        migrations.AddIndex(
            model_name="credentialrecord",
            index=models.Index(fields=["component", "credential_type"], name="cred_component_type_idx"),
        ),
    ]
