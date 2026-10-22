from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    # Tabla de settings.CACHES (DatabaseCache). El comando no hace nada si ya existe.
    call_command("createcachetable", database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):
    dependencies = []

    operations = [migrations.RunPython(create_cache_table, migrations.RunPython.noop)]
