from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views

urlpatterns = [
    path("", login_required(views.IndexView.as_view()), name="index"),
    path("weights", login_required(views.StrategyView.as_view()), name="strategies"),

    path("settings", views.settings_view, name="settings"),
    path("use_strategy/<int:id>", views.use_strategy, name="use_strategy"),
    path("update_prices", views.update_prices_view, name="update_prices"),
]
