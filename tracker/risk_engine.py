from datetime import timedelta
from typing import List, Dict, Any

from django.db.models import Q, Count
from django.utils import timezone

from .models import LabTest, PondLog, Incident, Lot, LotMovement, Node

# Standar mutu dan keamanan udang beku (ringkas dari tabel persyaratan)
# Keys mengikuti nama parameter di LabTest.parameter
STANDARD_LIMITS = {
    # Cemaran mikroba
    "ALT": {"limit": 1_000_000, "cmp": "<=", "severity": 25, "label": "Angka Lempeng Total"},
    "E.coli": {"limit": 1, "cmp": "<=", "severity": 40, "label": "E. coli"},
    "Salmonella": {"limit": 0, "cmp": "==", "severity": 60, "label": "Salmonella"},
    "Vibrio parahaemolyticus": {"limit": 10, "cmp": "<=", "severity": 40, "label": "Vibrio parahaemolyticus"},
    # Cemaran logam
    "Merkuri (Hg)": {"limit": 0.5, "cmp": "<=", "severity": 30},
    "Timbal (Pb)": {"limit": 0.2, "cmp": "<=", "severity": 30},
    "Kadmium (Cd)": {"limit": 0.1, "cmp": "<=", "severity": 30},
    # Residu antibiotik
    "Kloramfenikol": {"limit": 0, "cmp": "==", "severity": 60},
    "Metabolit Nitrofurans": {"limit": 0, "cmp": "==", "severity": 60},
    "Tetrasiklin": {"limit": 100, "cmp": "<=", "severity": 30},
}


def evaluate_lab_test(test: LabTest):
    """
    Cek satu hasil lab terhadap batas standar.
    Return: (violated: bool, delta_score: int, message: str)
    """
    spec = STANDARD_LIMITS.get(test.parameter)
    if not spec:
        return False, 0, None

    value = test.value
    limit = spec["limit"]
    cmp_op = spec["cmp"]
    severity = spec["severity"]
    label = spec.get("label", test.parameter)

    # treat missing value as violation for safety when comparator expects a value
    if value is None:
        violated = True
    elif cmp_op == "<=":
        violated = value > limit
    elif cmp_op == "<":
        violated = value >= limit
    elif cmp_op == "==":
        violated = value != limit
    else:
        violated = False

    unit = f" {test.unit}" if getattr(test, "unit", None) else ""
    if violated:
        message = f"{label} melebihi batas ({value}{unit}, limit {limit}) (+{severity})"
    else:
        message = f"{label} sesuai batas ({value}{unit}) (+0)"

    return violated, severity if violated else 0, message


def calculate_lot_risk(lot: Lot):
    """
    Hitung risk_score (0-100), risk_level (LOW/MEDIUM/HIGH),
    dan status (OK/HOLD/INVESTIGATE) secara otomatis.
    Faktor yang dipakai:
      - Reputasi farm (riwayat lot bermasalah & insiden)
      - Umur lot (sejak tanggal panen)
      - Volume lot (dampak kalau bermasalah)
      - Hasil lab terhadap batas standar
      - Insiden aktif
      - Kualitas air tambak (pH & salinitas terakhir)
    """

    score = 0
    critical_violation = False

    # === 0. Reputasi farm (riwayat lot bermasalah) ===
    if lot.farm:
        qs_farm_lots = Lot.objects.filter(farm=lot.farm)
        total_farm_lots = qs_farm_lots.count()
        problematic_lots = qs_farm_lots.filter(status__in=["HOLD", "INVESTIGATE"]).count()

        if total_farm_lots > 0:
            ratio = problematic_lots / total_farm_lots
            if ratio >= 0.5:
                score += 30
            elif ratio >= 0.2:
                score += 20
            elif ratio >= 0.1:
                score += 10

    # === 1. Umur lot (sejak harvest_date) ===
    if lot.harvest_date:
        today = timezone.now().date()
        days = (today - lot.harvest_date).days

        if days <= 2:
            score += 5  # masih sangat fresh
        elif days <= 5:
            score += 10
        elif days <= 10:
            score += 20
        else:
            score += 30  # sudah cukup lama -> risiko kualitas naik
    else:
        # tidak ada tanggal panen -> tambahkan sedikit risiko ketidakpastian
        score += 10

    # === 2. Volume lot (kg) ===
    if getattr(lot, "volume_kg", None):
        if lot.volume_kg > 5000:
            score += 15  # volume besar, dampak ekonominya besar
        elif lot.volume_kg > 1000:
            score += 10
        else:
            score += 5

    # === 3. Hasil lab ===
    labtests = LabTest.objects.filter(sampling__lot=lot)

    if not labtests.exists():
        score += 20  # belum ada hasil lab -> agak berisiko
    else:
        # evaluasi berdasarkan batas standar
        for test in labtests:
            violated, delta, _ = evaluate_lab_test(test)
            if violated:
                score += delta
                if delta >= 60:  # pelanggaran kritis (mikroba berbahaya / antibiotik terlarang)
                    critical_violation = True

        # fallback: uji yang belum dipetakan tetap lihat kolom result
        unmapped_fail = (
            labtests.exclude(parameter__in=STANDARD_LIMITS.keys())
            .filter(result__iexact="FAIL")
            .count()
        )
        score += unmapped_fail * 20

    # === 4. Insiden keamanan pangan ===
    if Incident.objects.filter(lot=lot).exclude(status__iexact="closed").exists():
        score += 30

    if lot.farm and Incident.objects.filter(lot__farm=lot.farm).exists():
        score += 10

    # === 5. Kualitas air terakhir di tambak ===
    if lot.farm:
        last_log = (
            PondLog.objects.filter(farm=lot.farm)
            .order_by("-date")
            .first()
        )
        if last_log:
            if last_log.ph is not None and (last_log.ph < 7 or last_log.ph > 8.5):
                score += 10
            if (
                last_log.salinity_ppt is not None
                and (last_log.salinity_ppt < 10 or last_log.salinity_ppt > 30)
            ):
                score += 10

    # clamp 0-100
    if critical_violation:
        score = max(score, 90)

    score = max(0, min(score, 100))

    if score >= 70:
        risk_level = "HIGH"
        status = "INVESTIGATE"
    elif score >= 40:
        risk_level = "MEDIUM"
        status = "HOLD"
    else:
        risk_level = "LOW"
        status = "OK"

    return score, risk_level, status


def explain_lot_risk(lot: Lot):
    """
    Versi explainable dari calculate_lot_risk:
    mengembalikan score, level, status, dan daftar alasan.
    """

    reasons = []
    score = 0
    critical_violation = False

    # === 0. Reputasi farm ===
    if lot.farm:
        qs_farm_lots = Lot.objects.filter(farm=lot.farm)
        total_farm_lots = qs_farm_lots.count()
        problematic_lots = qs_farm_lots.filter(status__in=["HOLD", "INVESTIGATE"]).count()

        if total_farm_lots > 0:
            ratio = problematic_lots / total_farm_lots
            if ratio >= 0.5:
                delta = 30
                reasons.append(f"Farm punya {problematic_lots}/{total_farm_lots} lot bermasalah (+{delta})")
                score += delta
            elif ratio >= 0.2:
                delta = 20
                reasons.append(f"Farm punya beberapa riwayat lot bermasalah (+{delta})")
                score += delta
            elif ratio >= 0.1:
                delta = 10
                reasons.append(f"Farm pernah punya lot bermasalah (+{delta})")
                score += delta

    # === 1. Umur lot ===
    if lot.harvest_date:
        today = timezone.now().date()
        days = (today - lot.harvest_date).days

        if days <= 2:
            delta = 5
            reasons.append(f"Umur lot sangat fresh ({days} hari) (+{delta})")
            score += delta
        elif days <= 5:
            delta = 10
            reasons.append(f"Umur lot {days} hari (+{delta})")
            score += delta
        elif days <= 10:
            delta = 20
            reasons.append(f"Umur lot {days} hari, mulai berisiko (+{delta})")
            score += delta
        else:
            delta = 30
            reasons.append(f"Umur lot {days} hari, cukup lama (+{delta})")
            score += delta
    else:
        delta = 10
        reasons.append(f"Tanggal panen tidak tercatat (+{delta})")
        score += delta

    # === 2. Volume ===
    if getattr(lot, "volume_kg", None):
        if lot.volume_kg > 5000:
            delta = 15
            reasons.append(f"Volume sangat besar ({lot.volume_kg} kg) (+{delta})")
            score += delta
        elif lot.volume_kg > 1000:
            delta = 10
            reasons.append(f"Volume cukup besar ({lot.volume_kg} kg) (+{delta})")
            score += delta
        else:
            delta = 5
            reasons.append(f"Volume kecil-sedang ({lot.volume_kg} kg) (+{delta})")
            score += delta

    # === 3. Hasil lab ===
    labtests = LabTest.objects.filter(sampling__lot=lot)
    if not labtests.exists():
        delta = 20
        reasons.append(f"Belum ada hasil lab untuk lot ini (+{delta})")
        score += delta
    else:
        for test in labtests:
            violated, delta, message = evaluate_lab_test(test)
            reasons.append(message or f"Hasil {test.parameter}: {test.result or '-'}")
            if violated:
                score += delta
                if delta >= 60:
                    critical_violation = True

        unmapped_fail = (
            labtests.exclude(parameter__in=STANDARD_LIMITS.keys())
            .filter(result__iexact="FAIL")
            .count()
        )
        if unmapped_fail:
            delta = unmapped_fail * 20
            reasons.append(f"{unmapped_fail} parameter uji (tanpa standar) dinyatakan FAIL (+{delta})")
            score += delta

    # === 4. Insiden ===
    if Incident.objects.filter(lot=lot).exclude(status__iexact="closed").exists():
        delta = 30
        reasons.append(f"Ada insiden aktif yang terkait langsung dengan lot (+{delta})")
        score += delta

    if lot.farm and Incident.objects.filter(lot__farm=lot.farm).exists():
        delta = 10
        reasons.append(f"Ada insiden lain di farm yang sama (+{delta})")
        score += delta

    # === 5. Kualitas air ===
    if lot.farm:
        last_log = (
            PondLog.objects.filter(farm=lot.farm)
            .order_by("-date")
            .first()
        )
        if last_log:
            if last_log.ph is not None and (last_log.ph < 7 or last_log.ph > 8.5):
                delta = 10
                reasons.append(f"pH air terakhir di luar rentang aman ({last_log.ph}) (+{delta})")
                score += delta
            if (
                last_log.salinity_ppt is not None
                and (last_log.salinity_ppt < 10 or last_log.salinity_ppt > 30)
            ):
                delta = 10
                reasons.append(f"Salinitas air terakhir di luar rentang aman ({last_log.salinity_ppt} ppt) (+{delta})")
                score += delta

    # clamp + mapping level & status (sama seperti calculate_lot_risk)
    if critical_violation:
        reasons.append("Pelanggaran kritis terhadap standar (mikroba/antibiotik), otomatis INVESTIGATE")
        score = max(score, 90)

    score = max(0, min(score, 100))

    if score >= 70:
        risk_level = "HIGH"
        status = "INVESTIGATE"
    elif score >= 40:
        risk_level = "MEDIUM"
        status = "HOLD"
    else:
        risk_level = "LOW"
        status = "OK"

    return {
        "score": score,
        "risk_level": risk_level,
        "status": status,
        "reasons": reasons,
    }


def estimate_node_contamination_probabilities(lot: Lot) -> List[Dict[str, Any]]:
    """
    Estimasi peluang kontaminasi per node pada journey lot.

    Metodologi sederhana:
    - Hitung total lot dan lot bermasalah (HOLD/INVESTIGATE) yang pernah melewati node tersebut.
    - Tambahkan sinyal insiden aktif yang terkait lot di node itu.
    - Normalisasi menjadi persentase sehingga bisa divisualisasikan di UI.
    """

    movements = (
        LotMovement.objects.filter(lot=lot)
        .select_related("node")
        .order_by("timestamp")
    )

    ordered_nodes: List[Node] = []
    seen: set[int] = set()
    for mv in movements:
        # simpan urutan node tanpa menduplikasi jika berturut-turut sama
        if mv.node_id not in seen or not ordered_nodes or ordered_nodes[-1].id != mv.node_id:
            ordered_nodes.append(mv.node)
            seen.add(mv.node_id)

    if not ordered_nodes:
        return []

    node_ids = [n.id for n in ordered_nodes]

    # agregasi lintas seluruh lot yang pernah lewat node-node terkait
    stats = (
        LotMovement.objects.filter(node_id__in=node_ids)
        .values("node_id")
        .annotate(
            lot_count=Count("lot", distinct=True),
            problematic_count=Count(
                "lot",
                filter=Q(lot__status__in=["HOLD", "INVESTIGATE"]),
                distinct=True,
            ),
            incident_count=Count(
                "lot__incidents",
                filter=~Q(lot__incidents__status="CLOSED"),
                distinct=True,
            ),
        )
    )

    stats_map = {item["node_id"]: item for item in stats}

    weights = []
    for node in ordered_nodes:
        node_stat = stats_map.get(
            node.id,
            {"lot_count": 0, "problematic_count": 0, "incident_count": 0},
        )
        if node_stat["lot_count"]:
            base_ratio = node_stat["problematic_count"] / node_stat["lot_count"]
        else:
            # jika belum ada riwayat, beri bobot kecil untuk tetap tampil di visualisasi
            base_ratio = 0.05

        # insiden aktif memberikan bobot tambahan per insiden
        incident_bonus = 0.03 * node_stat.get("incident_count", 0)
        weight = base_ratio + incident_bonus
        weights.append(max(weight, 0.01))

    total_weight = sum(weights) or 1

    result = []
    for node, weight in zip(ordered_nodes, weights):
        node_stat = stats_map.get(
            node.id,
            {"lot_count": 0, "problematic_count": 0, "incident_count": 0},
        )
        probability = round((weight / total_weight) * 100, 1)
        result.append(
            {
                "node_id": node.id,
                "node": node,
                "probability": probability,
                "lot_count": node_stat.get("lot_count", 0),
                "problematic_count": node_stat.get("problematic_count", 0),
                "incident_count": node_stat.get("incident_count", 0),
            }
        )

    return result
