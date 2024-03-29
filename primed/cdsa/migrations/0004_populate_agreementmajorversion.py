# Generated by Django 3.2.19 on 2023-08-31 18:58

from django.db import migrations


def populate_agreementversion_major_version_fk(apps, schema_editor):
    """Populate the AgreementMajorVersion model using major_versions in AgreementVersion,
    and set AgreementVersion.major_version_fk."""
    AgreementVersion = apps.get_model("cdsa", "AgreementVersion")
    AgreementMajorVersion = apps.get_model("cdsa", "AgreementMajorVersion")
    for row in AgreementVersion.objects.all():
        # Get or create the AgreementMajorVersion object.
        try:
            major_version = AgreementMajorVersion.objects.get(version=row.major_version)
        except AgreementMajorVersion.DoesNotExist:
            major_version = AgreementMajorVersion(
                version=row.major_version,
            )
            major_version.full_clean()
            major_version.save()
        # Set major_version_fk for the agreement_version object.
        row.major_version_fk = major_version
        row.save(update_fields=["major_version_fk"])


class Migration(migrations.Migration):

    dependencies = [
        ('cdsa', '0003_agreementversion_add_major_version_fk'),
    ]

    operations = [
        migrations.RunPython(populate_agreementversion_major_version_fk, reverse_code=migrations.RunPython.noop),
    ]
