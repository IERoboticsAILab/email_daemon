from django.db import models

class MailingList(models.Model):
    alias = models.CharField(max_length=100, unique=True)  # e.g., "msgs@cyphy.life"
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.alias

class Subscriber(models.Model):
    email = models.EmailField()
    mailing_lists = models.ManyToManyField(MailingList, related_name='subscribers')  # Changed from ForeignKey to ManyToManyField
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Remove unique_together since subscribers can be in multiple lists
        unique_together = []

    def __str__(self):
        lists = ", ".join([ml.alias for ml in self.mailing_lists.all()])
        return f"{self.email} -> [{lists}]"
