from django.shortcuts import render, get_object_or_404
from django.db.models import Count

from .models import Lot, Node, LotMovement


def lot_list(request):
    lots = Lot.objects.order_by("-created_at")
    return render(request, "tracker/lot_list.html", {"lots": lots})


def contaminated_lots(request):
    lots = Lot.objects.filter(status__in=["HOLD", "INVESTIGATE"]).order_by("-created_at")
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
    }
    return render(request, "tracker/lot_detail.html", context)


# Optional: placeholder untuk endpoint lain yang sudah ada di urls
from django.http import JsonResponse, HttpResponse


def lot_qr(request, lot_id: str):
    # Bisa nanti diisi generator QR asli;
    # sementara return placeholder saja.
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

