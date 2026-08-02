from django.db import migrations, models


def prepare_existing_accounts(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.all().iterator():
        if not user.email:
            user.email = f"legacy-{user.phone}@example.invalid"
            user.save(update_fields=["email"])
    apps.get_model("accounts", "OTPChallenge").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.RunPython(prepare_existing_accounts, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(max_length=254, unique=True),
        ),
        migrations.RemoveField(model_name="user", name="phone_verified"),
        migrations.RemoveField(model_name="user", name="phone"),
        migrations.RenameField(model_name="otpchallenge", old_name="phone", new_name="email"),
        migrations.AlterField(
            model_name="otpchallenge",
            name="email",
            field=models.EmailField(db_index=True, max_length=254),
        ),
    ]
