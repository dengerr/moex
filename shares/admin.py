from django.contrib import admin
from . import models


class ShareAdmin(admin.ModelAdmin):
    list_display = 'ticker', 'short_name'


admin.site.register(models.Share, ShareAdmin)
admin.site.register(models.Briefcase)
admin.site.register(models.Strategy)
admin.site.register(models.SharePriceBlock)
