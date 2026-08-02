from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def ensure_employer_profile(sender, instance, **kwargs):
    if instance.role == User.Role.EMPLOYER:
        from jobs.models import EmployerProfile

        EmployerProfile.objects.get_or_create(user=instance, defaults={"company_name": instance.full_name or "My business"})


@receiver(pre_save, sender=User)
def delete_replaced_resume(sender, instance, **kwargs):
    if not instance.pk:
        return
    previous = User.objects.filter(pk=instance.pk).only("resume").first()
    if previous and previous.resume and previous.resume.name != instance.resume.name:
        storage = previous.resume.storage
        name = previous.resume.name
        transaction.on_commit(lambda: storage.delete(name))


@receiver(post_delete, sender=User)
def delete_user_resume(sender, instance, **kwargs):
    if instance.resume:
        storage = instance.resume.storage
        name = instance.resume.name
        transaction.on_commit(lambda: storage.delete(name))
