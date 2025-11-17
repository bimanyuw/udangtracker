from datetime import timedelta

from django.utils import timezone
from .models import LabTest, PondLog, Incident, Lot


def calculate_lot_risk(lot: Lot):
    """
    Hitung risk_score (0–100), risk_level (LOW/MEDIUM/HIGH),
    dan status (OK/HOLD/INVESTIGATE) secara otomatis.
    Faktor yang dipakai:
      - Reputasi farm (riwayat lot bermasalah & insiden)
      - Umur lot (sejak tanggal panen)
      - Volume lot (dampak kalau bermasalah)
      - Hasil lab (PASS/FAIL)
      - Insiden aktif
      - Kualitas air tambak (pH & salinitas terakhir)
    """

    score = 0

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
            score += 5      # masih sangat fresh
        elif days <= 5:
            score += 10
        elif days <= 10:
            score += 20
        else:
            score += 30     # sudah cukup lama → risiko kualitas naik
    else:
        # tidak ada tanggal panen → tambahkan sedikit risiko ketidakpastian
        score += 10

    # === 2. Volume lot (kg) ===
    if getattr(lot, "volume_kg", None):
        if lot.volume_kg > 5000:
            score += 15   # volume besar, dampak ekonominya besar
        elif lot.volume_kg > 1000:
            score += 10
        else:
            score += 5

    # === 3. Hasil lab ===
    labtests = LabTest.objects.filter(sampling__lot=lot)

    if not labtests.exists():
        # belum ada hasil lab → agak berisiko
        score += 20
    else:
        fail_count = labtests.filter(result__iexact="FAIL").count()
        score += fail_count * 25  # tiap gagal uji nambah 25

    # === 4. Insiden keamanan pangan ===
    # insiden aktif untuk lot ini
    if Incident.objects.filter(lot=lot).exclude(status__iexact="closed").exists():
        score += 30

    # insiden lain di farm yang sama
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
            # contoh rule: pH & salinitas di luar rentang normal
            if last_log.ph is not None and (last_log.ph < 7 or last_log.ph > 8.5):
                score += 10
            if (
                last_log.salinity_ppt is not None
                and (last_log.salinity_ppt < 10 or last_log.salinity_ppt > 30)
            ):
                score += 10

    # clamp 0–100
    score = max(0, min(score, 100))

    # === 6. Risk level & status dari score ===
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
        from django.utils import timezone
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
            reasons.append(f"Volume kecil–sedang ({lot.volume_kg} kg) (+{delta})")
            score += delta

    # === 3. Hasil lab ===
    labtests = LabTest.objects.filter(sampling__lot=lot)
    if not labtests.exists():
        delta = 20
        reasons.append(f"Belum ada hasil lab untuk lot ini (+{delta})")
        score += delta
    else:
        fail_count = labtests.filter(result__iexact="FAIL").count()
        if fail_count:
            delta = fail_count * 25
            reasons.append(f"{fail_count} parameter uji lab dinyatakan FAIL (+{delta})")
            score += delta
        else:
            reasons.append("Semua hasil lab PASS (+0)")

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
