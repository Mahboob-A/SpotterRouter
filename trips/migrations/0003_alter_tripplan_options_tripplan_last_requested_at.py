from typing import Any

from django.db import migrations, models


def populate_last_requested_at(apps: Any, schema_editor: Any) -> None:
    TripPlan = apps.get_model("trips", "TripPlan")
    TripPlan.objects.filter(last_requested_at__isnull=True).update(
        last_requested_at=models.F("created_at")
    )


def reverse_populate(apps: Any, schema_editor: Any) -> None:
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("trips", "0002_tripplan_pricing_dataset"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="tripplan",
            options={"ordering": ["-last_requested_at", "-created_at"]},
        ),
        migrations.AddField(
            model_name="tripplan",
            name="last_requested_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(populate_last_requested_at, reverse_populate),
    ]
