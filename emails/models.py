from django.db import models

class MailingList(models.Model):
    alias = models.CharField(max_length=100, unique=True)  # e.g., "robotics-team@yourdomain.com"
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.alias

class Subscriber(models.Model):
    mailing_list = models.ForeignKey(MailingList, on_delete=models.CASCADE, related_name='subscribers')
    email = models.EmailField()
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['mailing_list', 'email']

    def __str__(self):
        return f"{self.email} -> {self.mailing_list.alias}"
