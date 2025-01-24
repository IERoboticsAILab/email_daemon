from django.contrib import admin
from .models import MailingList, Subscriber

@admin.register(MailingList)
class MailingListAdmin(admin.ModelAdmin):
    list_display = ('alias', 'description', 'created_at')
    search_fields = ('alias', 'description')

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'get_mailing_lists', 'is_active', 'added_at')
    list_filter = ('mailing_lists', 'is_active')
    search_fields = ('email',)
    filter_horizontal = ('mailing_lists',)

    def get_mailing_lists(self, obj):
        return ", ".join([ml.alias for ml in obj.mailing_lists.all()])
    get_mailing_lists.short_description = 'Mailing Lists'
