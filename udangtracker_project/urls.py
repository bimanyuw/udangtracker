# udangtracker_project/urls.py

from django.contrib import admin
from django.urls import path, include
from tracker import views as tracker_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("tracker.urls")),
    path("authenticate/", include("authenticate.urls")),
]