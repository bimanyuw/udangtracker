from django.urls import path
from . import views

app_name = "tracker"

urlpatterns = [
    path("lots/", views.lot_list, name="lot_list"),

    path("lots/contaminated/", views.contaminated_lots, name="contaminated_lots"),

    path("trace/suspects/", views.suspect_nodes, name="suspect_nodes"),

    path("lots/<str:lot_id>/", views.lot_detail, name="lot_detail"),
    path("lots/<str:lot_id>/qr/", views.lot_qr, name="lot_qr"),
    path("lots/<str:lot_id>/trace.json", views.lot_trace_json, name="lot_trace_json"),
]
