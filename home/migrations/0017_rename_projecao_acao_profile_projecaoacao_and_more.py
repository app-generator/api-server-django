# Generated by Django 4.1.5 on 2023-01-13 19:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0016_profile_menu_ranking'),
    ]

    operations = [
        migrations.RenameField(
            model_name='profile',
            old_name='projecao_acao',
            new_name='projecaoacao',
        ),
        migrations.RenameField(
            model_name='rankeamento',
            old_name='projecao_acao',
            new_name='projecaoacao',
        ),
        migrations.AlterUniqueTogether(
            name='rankeamento',
            unique_together={('projecaoacao', 'ranking')},
        ),
    ]
