from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_cache_table"),
    ]

    operations = [
        migrations.CreateModel(
            name="RateCounter",
            fields=[
                ("key", models.CharField(max_length=200, primary_key=True, serialize=False)),
                ("window_start", models.DateTimeField(db_index=True)),
                ("count", models.PositiveIntegerField(default=0)),
            ],
            options={"db_table": "core_ratecounter"},
        ),
    ]
