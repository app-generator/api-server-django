# Generated by Django 4.1.5 on 2023-01-24 11:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0022_alter_profile_telefone'),
    ]

    operations = [
        migrations.RenameField(
            model_name='profile',
            old_name='telefone',
            new_name='celular',
        ),
    ]
