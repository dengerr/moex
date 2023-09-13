from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views

urlpatterns = [
    path("", login_required(views.IndexView.as_view()), name="index"),
    path("settings", login_required(views.settings_view), name="settings"),
    path("update_prices", login_required(views.update_prices_view), name="update_prices"),
    path("weights", login_required(views.StrategyView.as_view()), name="strategies"),
]
