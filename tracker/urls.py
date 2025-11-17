from django.urls import path
from . import views

app_name = "tracker"

urlpatterns = [
    # HOME → sementara redirect ke daftar lot
    path("", views.home_redirect, name="home"),

    # ========== LOT CORE ==========
    path("lots/", views.lot_list, name="lot_list"),

    # LOT yang terkontaminasi (SUDAH ADA)
    path("lots/contaminated/", views.contaminated_lots, name="contaminated_lots"),

    # GRAF / NETWORK SUSPECT (SUDAH ADA)
    path("trace/suspects/", views.suspect_nodes, name="suspect_nodes"),

    # DETAIL LOT BERDASAR lot_id (bukan pk)
    path("lots/<str:lot_id>/", views.lot_detail, name="lot_detail"),

    # QR PAGE & TRACE JSON (SUDAH ADA)
    path("lots/<str:lot_id>/qr/", views.lot_qr, name="lot_qr"),
    path("lots/<str:lot_id>/trace.json", views.lot_trace_json, name="lot_trace_json"),

    # ========== FARMS ==========
    path("farms/", views.farm_list, name="farm_list"),
    path("farms/<int:pk>/", views.farm_detail, name="farm_detail"),

    # ========== DASHBOARD ==========
    path("dashboard/", views.dashboard, name="dashboard"),

    # ========== INCIDENTS ==========
    path("incidents/", views.incident_list, name="incident_list"),
    path("incidents/<int:pk>/", views.incident_detail, name="incident_detail"),

    # ========== PUBLIC QR VIEW ==========
    path("public/lot/<str:token>/", views.public_lot, name="public_lot"),
]
