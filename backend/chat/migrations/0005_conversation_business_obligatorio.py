import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0004_asignar_negocio_piloto"),
    ]

    operations = [
        migrations.AlterField(
            model_name="conversation",
            name="business",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="conversations",
                to="tenants.business",
            ),
        ),
        migrations.AddConstraint(
            model_name="conversation",
            constraint=models.CheckConstraint(
                condition=models.Q(("user__isnull", False), ("visitor__isnull", False), _connector="OR"),
                name="conv_tiene_cliente_o_visitante",
            ),
        ),
    ]
