# Generated by Django 4.2.8 on 2024-05-15 03:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ecommerce', '0009_orderproductcolorfield_delete_orderextrafield'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='OrderProductColorField',
            new_name='OrderProductColor',
        ),
    ]
