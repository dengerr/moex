from django.contrib import admin
from . import models


admin.site.register(models.Share)
admin.site.register(models.Briefcase)
admin.site.register(models.Strategy)
admin.site.register(models.SharePriceBlock)
