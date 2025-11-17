from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count
from django.http import JsonResponse, HttpResponse

from .models import Lot, Node, LotMovement, Farm
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404

from .forms import LotForm
from .risk_engine import calculate_lot_risk
from .risk_engine import explain_lot_risk

from django.db.models import Count, Q
from .models import Lot, Farm, Incident, LotMovement
from .models import Incident, IncidentRelatedLot


# ============ HOME REDIRECT ============

def home_redirect(request):
    return redirect("tracker:dashboard")

# ============ LOT CORE ============

def lot_list(request):
    lots = Lot.objects.all().order_by("-created_at")

    # ambil query string
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "all")

    # filter search Lot ID
    if q:
        lots = lots.filter(lot_id__icontains=q)

    # filter status
    if status in ["OK", "HOLD", "INVESTIGATE"]:
        lots = lots.filter(status=status)

    context = {
        "lots": lots,
        "q": q,
        "status": status,
    }
    return render(request, "tracker/lot_list.html", context)


def contaminated_lots(request):
    lots = Lot.objects.filter(status__in=["HOLD", "INVESTIGATE"]).order_by(
        "-created_at"
    )
    return render(request, "tracker/contaminated_lots.html", {"lots": lots})


def suspect_nodes(request):
    problematic_lots = Lot.objects.filter(status__in=["HOLD", "INVESTIGATE"])
    movements = LotMovement.objects.filter(lot__in=problematic_lots)

    suspects_raw = (
        movements.values("node__id", "node__name", "node__type")
        .annotate(
            movement_count=Count("id"),
            lots_count=Count("lot", distinct=True),
        )
        .order_by("-movement_count")
    )

    suspects = []
    for item in suspects_raw:
        node_id = item["node__id"]
        lots_involved = (
            movements.filter(node_id=node_id)
            .values_list("lot__lot_id", flat=True)
            .distinct()
        )

        # scoring risiko sederhana
        if item["movement_count"] >= 10:
            risk = "Tinggi"
        elif item["movement_count"] >= 5:
            risk = "Sedang"
        else:
            risk = "Rendah"

        suspects.append(
            {
                "name": item["node__name"],
                "type": item["node__type"],
                "movement_count": item["movement_count"],
                "lots_count": item["lots_count"],
                "lots": list(lots_involved),
                "risk": risk,
            }
        )

    context = {
        "problematic_lots": problematic_lots,
        "suspects": suspects,
    }
    return render(request, "tracker/suspect_nodes.html", context)


def lot_detail(request, lot_id: str):
    lot = get_object_or_404(Lot, lot_id=lot_id)

    movements = (
        LotMovement.objects.filter(lot=lot)
        .select_related("node")
        .order_by("timestamp")
    )

    path_nodes = [mv.node for mv in movements]

    context = {
        "lot": lot,
        "movements": movements,
        "path_nodes": path_nodes,
        # nanti di sini bisa ditambah:
        # - samplings / lab tests
        # - documents
        # - incidents
    }
    return render(request, "tracker/lot_detail.html", context)


def lot_qr(request, lot_id: str):
    # TODO: nanti bisa diganti render template berisi QR beneran
    return HttpResponse(f"QR endpoint for lot {lot_id}", content_type="text/plain")


def lot_trace_json(request, lot_id: str):
    lot = get_object_or_404(Lot, lot_id=lot_id)
    movements = (
        LotMovement.objects.filter(lot=lot)
        .select_related("node")
        .order_by("timestamp")
    )

    data = {
        "lot_id": lot.lot_id,
        "status": lot.status,
        "movements": [
            {
                "timestamp": mv.timestamp.isoformat(),
                "node": mv.node.name,
                "type": mv.node.type,
            }
            for mv in movements
        ],
    }
    return JsonResponse(data)


# ============ FARMS ============

def farm_list(request):
    farms = Farm.objects.all().order_by("name")
    context = {
        "farms": farms,
    }
    return render(request, "tracker/farm_list.html", context)


def farm_detail(request, pk):
    farm = get_object_or_404(Farm, pk=pk)
    # nanti di sini bisa tampilkan PondLog & ringkasan risk
    context = {
        "farm": farm,
    }
    return render(request, "tracker/farm_detail.html", context)


# ============ DASHBOARD ============

def dashboard(request):
    # TODO: diisi modul dashboard (query agregat)
    context = {}
    return render(request, "tracker/dashboard.html", context)


# ============ INCIDENTS ============

def incident_list(request):
    # TODO: diisi pakai model Incident
    context = {}
    return render(request, "tracker/incident_list.html", context)


def incident_detail(request, pk):
    # TODO: ganti dengan get_object_or_404(Incident, pk=pk)
    context = {"incident_id": pk}
    return render(request, "tracker/incident_detail.html", context)


# ============ PUBLIC VIEW QR ============

def public_lot(request, token):
    lot = get_object_or_404(Lot, public_token=token)
    context = {
        "lot": lot,
    }
    return render(request, "tracker/public_lot.html", context)

def lot_create(request):
    # hanya admin/staff yang boleh
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponseForbidden("Anda tidak memiliki izin untuk menambahkan lot.")

    if request.method == "POST":
        form = LotForm(request.POST)
        if form.is_valid():
            lot = form.save(commit=False)
            lot.creator = request.user

            # hitung risk & status awal pakai algoritma
            score, level, status = calculate_lot_risk(lot)
            lot.risk_score = score
            lot.risk_level = level
            lot.status = status

            lot.save()
            return redirect("tracker:lot_detail", lot_id=lot.lot_id)
    else:
        form = LotForm()

    return render(request, "tracker/lot_form.html", {"form": form})

def lot_detail(request, lot_id: str):
    lot = get_object_or_404(Lot, lot_id=lot_id)

    movements = (
        LotMovement.objects.filter(lot=lot)
        .select_related("node")
        .order_by("timestamp")
    )
    path_nodes = [mv.node for mv in movements]

    risk_info = explain_lot_risk(lot)

    context = {
        "lot": lot,
        "movements": movements,
        "path_nodes": path_nodes,
        "risk_info": risk_info,
    }
    return render(request, "tracker/lot_detail.html", context)

def dashboard(request):
    lots = Lot.objects.all()

    # --- Ringkasan lot ---
    total_lots = lots.count()
    status_counts = {
        "OK": lots.filter(status="OK").count(),
        "HOLD": lots.filter(status="HOLD").count(),
        "INVESTIGATE": lots.filter(status="INVESTIGATE").count(),
    }
    risk_counts = {
        "LOW": lots.filter(risk_level="LOW").count(),
        "MEDIUM": lots.filter(risk_level="MEDIUM").count(),
        "HIGH": lots.filter(risk_level="HIGH").count(),
    }

    # Lot bermasalah terbaru
    recent_problem_lots = (
        lots.filter(status__in=["HOLD", "INVESTIGATE"])
        .select_related("farm")
        .order_by("-created_at")[:5]
    )

    # --- Ringkasan insiden ---
    incidents = Incident.objects.all()
    incident_counts = {
        "total": incidents.count(),
        "open": incidents.exclude(status__iexact="closed").count(),
        "closed": incidents.filter(status__iexact="closed").count(),
    }

    # --- Tambak dengan performa paling bermasalah ---
    farms = Farm.objects.annotate(
        lot_count=Count("lots"),
        problematic_lot_count=Count(
            "lots", filter=Q(lots__status__in=["HOLD", "INVESTIGATE"])
        ),
    ).filter(lot_count__gt=0)


    top_farms = farms.order_by("-problematic_lot_count")[:5]

    # --- Node yang sering muncul di lot bermasalah ---
    movements = LotMovement.objects.filter(
        lot__status__in=["HOLD", "INVESTIGATE"]
    )
    top_nodes = (
        movements.values("node__name", "node__type")
        .annotate(
            movement_count=Count("id"),
            lots_count=Count("lot", distinct=True),
        )
        .order_by("-movement_count")[:5]
    )

    context = {
        "total_lots": total_lots,
        "status_counts": status_counts,
        "risk_counts": risk_counts,
        "incident_counts": incident_counts,
        "recent_problem_lots": recent_problem_lots,
        "top_farms": top_farms,
        "top_nodes": top_nodes,
    }
    return render(request, "tracker/dashboard.html", context)

def incident_list(request):
    incidents = Incident.objects.select_related("lot").order_by("-date")

    # filter & search sederhana
    status_filter = request.GET.get("status", "all")
    q = request.GET.get("q", "").strip()

    if status_filter == "open":
        incidents = incidents.exclude(status__iexact="closed")
    elif status_filter == "closed":
        incidents = incidents.filter(status__iexact="closed")

    if q:
        incidents = incidents.filter(
            Q(lot__lot_id__icontains=q) |
            Q(incident_type__icontains=q)
        )

    # ringkasan angka
    total_incidents = Incident.objects.count()
    open_incidents = Incident.objects.exclude(status__iexact="closed").count()
    closed_incidents = Incident.objects.filter(status__iexact="closed").count()

    # hitung jumlah lot terkait per insiden
    related_counts = (
        IncidentRelatedLot.objects
        .values("incident_id")
        .annotate(total=Count("lot_id"))
    )
    related_map = {row["incident_id"]: row["total"] for row in related_counts}

    # tambahkan 1 untuk lot utama (field incident.lot)
    for inc in incidents:
        inc.related_lot_count = related_map.get(inc.id, 0) + (1 if inc.lot_id else 0)

    context = {
        "incidents": incidents,
        "status_filter": status_filter,
        "q": q,
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "closed_incidents": closed_incidents,
    }
    return render(request, "tracker/incident_list.html", context)


def incident_detail(request, pk: int):
    incident = get_object_or_404(
        Incident.objects.select_related("lot", "lot__farm"),
        pk=pk,
    )

    related_lots = (
        IncidentRelatedLot.objects
        .filter(incident=incident)
        .select_related("lot", "lot__farm")
    )

    context = {
        "incident": incident,
        "related_lots": related_lots,
    }
    return render(request, "tracker/incident_detail.html", context)


