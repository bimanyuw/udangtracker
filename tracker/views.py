import base64
import io

import qrcode
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import LotForm
from .models import (
    Document,
    Farm,
    Incident,
    IncidentRelatedLot,
    LabTest,
    Lot,
    LotMovement,
    Node,
)
from .risk_engine import (
    calculate_lot_risk,
    explain_lot_risk,
    estimate_node_contamination_probabilities,
)


# ============ HOME REDIRECT ============

def home_redirect(request):
    return redirect("tracker:dashboard")


# ============ LOT CORE ============

def lot_list(request):
    lots = Lot.objects.all().order_by("-created_at")

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "all")

    if q:
        lots = lots.filter(lot_id__icontains=q)

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


def _generate_lot_qr_data(public_url: str) -> str:
    """Generate QR PNG and return data URI string."""

    image = qrcode.make(public_url)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    base64_data = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/png;base64,{base64_data}"


def lot_detail(request, lot_id: str):
    lot = get_object_or_404(Lot, lot_id=lot_id)

    movements = (
        LotMovement.objects.filter(lot=lot)
        .select_related("node")
        .order_by("timestamp")
    )

    # urutan node unik sesuai pergerakan
    path_nodes = []
    last_node_id = None
    for mv in movements:
        if mv.node_id != last_node_id:
            path_nodes.append({
                "id": mv.node_id,
                "name": mv.node.name,
                "type": mv.node.type,
                "timestamp": mv.timestamp,
            })
            last_node_id = mv.node_id

    node_risks = estimate_node_contamination_probabilities(lot)
    node_risk_map = {item["node_id"]: item for item in node_risks}

    path_nodes_enriched = []
    for node in path_nodes:
        stats = node_risk_map.get(node["id"])
        path_nodes_enriched.append(
            {
                **node,
                "chance": stats.get("probability") if stats else None,
                "lot_count": stats.get("lot_count", 0) if stats else 0,
                "problematic_count": stats.get("problematic_count", 0)
                if stats
                else 0,
            }
        )

    risk_info = explain_lot_risk(lot)

    # gabungkan hasil uji lab
    samplings = lot.samplings.prefetch_related("tests").order_by("-date")
    lab_tests = []
    for sampling in samplings:
        for test in sampling.tests.all():
            lab_tests.append(
                {
                    "sampling_date": sampling.date,
                    "parameter": test.parameter,
                    "value": test.value,
                    "unit": test.unit,
                    "limit_value": test.limit_value,
                    "result": test.result,
                }
            )

    documents = (
        Document.objects.filter(Q(lot=lot) | Q(farm=lot.farm))
        .order_by("-issue_date", "-created_at")
        .distinct()
    )

    incidents = lot.incidents.select_related("lot", "lot__farm").order_by("-date")

    public_url = request.build_absolute_uri(
        reverse("tracker:public_lot", args=[lot.public_token])
    )
    qr_data_uri = _generate_lot_qr_data(public_url)

    context = {
        "lot": lot,
        "movements": movements,
        "path_nodes": path_nodes_enriched,
        "risk_info": risk_info,
        "lab_tests": lab_tests,
        "documents": documents,
        "incidents": incidents,
        "public_url": public_url,
        "qr_data_uri": qr_data_uri,
    }
    return render(request, "tracker/lot_detail.html", context)


def lot_qr(request, lot_id: str):
    lot = get_object_or_404(Lot, lot_id=lot_id)
    public_url = request.build_absolute_uri(
        reverse("tracker:public_lot", args=[lot.public_token])
    )

    image = qrcode.make(public_url)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


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


def lot_create(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponseForbidden("Anda tidak memiliki izin untuk menambahkan lot.")

    if request.method == "POST":
        form = LotForm(request.POST)
        if form.is_valid():
            lot = form.save(commit=False)
            lot.creator = request.user

            score, level, status = calculate_lot_risk(lot)
            lot.risk_score = score
            lot.risk_level = level
            lot.status = status

            lot.save()
            return redirect("tracker:lot_detail", lot_id=lot.lot_id)
    else:
        form = LotForm()

    return render(request, "tracker/lot_form.html", {"form": form})


# ============ FARMS ============

def farm_list(request):
    farms = Farm.objects.all().order_by("name")
    context = {
        "farms": farms,
    }
    return render(request, "tracker/farm_list.html", context)


def farm_detail(request, pk):
    farm = get_object_or_404(Farm, pk=pk)
    context = {
        "farm": farm,
    }
    return render(request, "tracker/farm_detail.html", context)


# ============ DASHBOARD ============

def dashboard(request):
    lots = Lot.objects.all()

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

    recent_problem_lots = (
        lots.filter(status__in=["HOLD", "INVESTIGATE"])
        .select_related("farm")
        .order_by("-created_at")[:5]
    )

    incidents = Incident.objects.all()
    incident_counts = {
        "total": incidents.count(),
        "open": incidents.exclude(status__iexact="closed").count(),
        "closed": incidents.filter(status__iexact="closed").count(),
    }

    farms = Farm.objects.annotate(
        lot_count=Count("lots"),
        problematic_lot_count=Count(
            "lots", filter=Q(lots__status__in=["HOLD", "INVESTIGATE"])
        ),
    ).filter(lot_count__gt=0)

    top_farms = farms.order_by("-problematic_lot_count")[:5]

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


# ============ INCIDENTS ============

def incident_list(request):
    incidents = Incident.objects.select_related("lot").order_by("-date")

    status_filter = request.GET.get("status", "all")
    q = request.GET.get("q", "").strip()

    if status_filter == "open":
        incidents = incidents.exclude(status__iexact="closed")
    elif status_filter == "closed":
        incidents = incidents.filter(status__iexact="closed")

    if q:
        incidents = incidents.filter(
            Q(lot__lot_id__icontains=q) | Q(incident_type__icontains=q)
        )

    total_incidents = Incident.objects.count()
    open_incidents = Incident.objects.exclude(status__iexact="closed").count()
    closed_incidents = Incident.objects.filter(status__iexact="closed").count()

    related_counts = IncidentRelatedLot.objects.values("incident_id").annotate(
        total=Count("lot_id")
    )
    related_map = {row["incident_id"]: row["total"] for row in related_counts}

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

    related_lots = IncidentRelatedLot.objects.filter(incident=incident).select_related(
        "lot", "lot__farm"
    )

    context = {
        "incident": incident,
        "related_lots": related_lots,
    }
    return render(request, "tracker/incident_detail.html", context)


# ============ PUBLIC VIEW ============

def public_lot(request, token):
    lot = get_object_or_404(Lot, public_token=token)
    context = {
        "lot": lot,
    }
    return render(request, "tracker/public_lot.html", context)


