# udangtracker_project/urls.py

from django.contrib import admin
from django.urls import path, include
from tracker import views as tracker_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", tracker_views.lot_list, name="home"),
    path("", include("tracker.urls")),
]
