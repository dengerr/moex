from django.contrib import admin
from . import models


class ShareAdmin(admin.ModelAdmin):
    list_display = 'ticker', 'short_name'


class RowAdmin(admin.ModelAdmin):
    list_display = 'id', 'briefcase', 'share', 'count'


admin.site.register(models.Share, ShareAdmin)
admin.site.register(models.Briefcase)
admin.site.register(models.Row, RowAdmin)
admin.site.register(models.Strategy)
admin.site.register(models.SharePriceBlock)
