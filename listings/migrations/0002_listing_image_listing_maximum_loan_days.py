from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="image",
            field=models.ImageField(
                blank=True,
                upload_to="listing_images/",
            ),
        ),
        migrations.AddField(
            model_name="listing",
            name="maximum_loan_days",
            field=models.PositiveIntegerField(
                default=7,
                help_text="Longest number of days one borrower may keep the item.",
                validators=[MinValueValidator(1)],
            ),
        ),
    ]
