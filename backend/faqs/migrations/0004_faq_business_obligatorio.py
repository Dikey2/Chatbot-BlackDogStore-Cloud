import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("faqs", "0003_asignar_negocio_piloto"),
    ]

    operations = [
        migrations.AlterField(
            model_name="faq",
            name="business",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="faqs", to="tenants.business"
            ),
        ),
    ]
