# tracker/views.py
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.urls import reverse
from django.db.models import Prefetch
from django.http import JsonResponse


from .models import Lot

import qrcode
from io import BytesIO
from collections import Counter
from django.db.models import Q



def lot_list(request):
    """
    Menampilkan daftar semua lot udang.
    """
    lots = Lot.objects.all().order_by("-created_at")
    context = {
        "lots": lots,
    }
    return render(request, "tracker/lot_list.html", context)


def lot_detail(request, lot_id):
    lot = get_object_or_404(
        Lot.objects.prefetch_related(
            "movements__node_from",
            "movements__node_to",
            "qc_results__node_at",
        ),
        lot_id=lot_id,
    )

    movements = lot.movements.all().order_by("timestamp")
    qc_results = lot.qc_results.all().order_by("timestamp")

    context = {
        "lot": lot,
        "movements": movements,
        "qc_results": qc_results,
    }
    return render(request, "tracker/lot_detail.html", context)


def lot_qr(request, lot_id):
    lot = get_object_or_404(Lot, lot_id=lot_id)

    # URL absolut ke halaman detail lot
    detail_url = request.build_absolute_uri(
        reverse("tracker:lot_detail", args=[lot.lot_id])
    )

    # Generate QR code
    qr_img = qrcode.make(detail_url)

    buffer = BytesIO()
    qr_img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    return HttpResponse(image_bytes, content_type="image/png")

def suspect_nodes(request):
    """
    Analisis node yang paling sering muncul di lot bermasalah
    (status HOLD / INVESTIGATE).
    """
    # 1) Ambil semua lot bermasalah
    bad_lots = (
        Lot.objects
        .filter(status__in=["HOLD", "INVESTIGATE"])
        .prefetch_related(
            "movements__node_from",
            "movements__node_to",
        )
        .order_by("-created_at")
    )

    node_counter = Counter()
    node_lot_map = {}  # node_id -> { "node": Node, "lot_ids": set([...]) }

    for lot in bad_lots:
        for mv in lot.movements.all():
            for node in (mv.node_from, mv.node_to):
                if node is None:
                    continue
                node_id = node.id
                node_counter[node_id] += 1

                data = node_lot_map.setdefault(
                    node_id,
                    {"node": node, "lot_ids": set()},
                )
                data["lot_ids"].add(lot.lot_id)

    # Suspect list yang siap dikirim ke template
    suspects = []
    for node_id, data in node_lot_map.items():
        node = data["node"]
        lot_ids = sorted(data["lot_ids"])
        suspects.append({
            "node": node,
            "count": node_counter[node_id],
            "lots_count": len(lot_ids),
            "lots": lot_ids,
        })

    # Urutkan dari yang paling sering muncul
    suspects.sort(key=lambda x: x["count"], reverse=True)

    context = {
        "bad_lots": bad_lots,
        "suspects": suspects,
    }
    return render(request, "tracker/suspect_nodes.html", context)

def contaminated_lots(request):
    """
    Menampilkan semua lot yang punya setidaknya satu QC is_contaminated=True.
    """
    lots = (
        Lot.objects
        .filter(qc_results__is_contaminated=True)
        .distinct()
        .order_by("-created_at")
    )

    context = {
        "lots": lots,
    }
    return render(request, "tracker/contaminated_lots.html", context)

def lot_trace_json(request, lot_id):
    """
    Mengembalikan jalur pergerakan lot dalam bentuk JSON.
    Cocok buat dipakai front-end graf.
    """
    lot = get_object_or_404(
        Lot.objects.prefetch_related(
            "movements__node_from",
            "movements__node_to",
        ),
        lot_id=lot_id,
    )

    movements = lot.movements.all().order_by("timestamp")

    nodes = {}
    links = []

    # Kumpulkan node
    for mv in movements:
        if mv.node_from:
            nodes[mv.node_from.id] = {
                "id": mv.node_from.id,
                "name": mv.node_from.name,
                "type": mv.node_from.type,
            }
        if mv.node_to:
            nodes[mv.node_to.id] = {
                "id": mv.node_to.id,
                "name": mv.node_to.name,
                "type": mv.node_to.type,
            }
        if mv.node_from and mv.node_to:
            links.append({
                "source": mv.node_from.id,
                "target": mv.node_to.id,
                "timestamp": mv.timestamp.isoformat(),
            })

    data = {
        "lot_id": lot.lot_id,
        "status": lot.status,
        "nodes": list(nodes.values()),
        "links": links,
    }
    return JsonResponse(data)
