from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0008_alter_opstodoitem_options_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="opstodoitem",
            name="assigned_to",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ops_todos_assigned",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
