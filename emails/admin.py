from django.contrib import admin
from .models import MailingList, Subscriber

@admin.register(MailingList)
class MailingListAdmin(admin.ModelAdmin):
    list_display = ('alias', 'description', 'created_at')
    search_fields = ('alias', 'description')

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'mailing_list', 'is_active', 'added_at')
    list_filter = ('mailing_list', 'is_active')
    search_fields = ('email',)
