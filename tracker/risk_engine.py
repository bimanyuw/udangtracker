from .models import LabTest, PondLog, Incident, Lot


def calculate_lot_risk(lot: Lot):
    """
    Hitung risk_score (0–100), risk_level (LOW/MEDIUM/HIGH),
    dan status (OK/HOLD/INVESTIGATE) secara otomatis.
    Rule-nya masih sederhana tapi mudah dijelaskan ke juri.
    """
    score = 0

    # === 1. Hasil lab ===
    labtests = LabTest.objects.filter(sampling__lot=lot)

    if not labtests.exists():
        # belum ada hasil lab → agak berisiko
        score += 20
    else:
        fail_count = labtests.filter(result__iexact="FAIL").count()
        score += fail_count * 25  # tiap gagal uji nambah 25

    # === 2. Insiden keamanan pangan ===
    # insiden aktif untuk lot ini
    if Incident.objects.filter(lot=lot).exclude(status__iexact="closed").exists():
        score += 30

    # insiden lain di farm yang sama
    if lot.farm and Incident.objects.filter(lot__farm=lot.farm).exists():
        score += 10

    # === 3. Kualitas air terakhir di tambak ===
    if lot.farm:
        last_log = (
            PondLog.objects.filter(farm=lot.farm)
            .order_by("-date")
            .first()
        )
        if last_log:
            # contoh rule: pH & salinitas di luar rentang normal
            if last_log.ph and (last_log.ph < 7 or last_log.ph > 8.5):
                score += 10
            if last_log.salinity_ppt and (last_log.salinity_ppt < 10 or last_log.salinity_ppt > 30):
                score += 10

    # clamp 0–100
    score = max(0, min(score, 100))

    # === 4. Risk level & status dari score ===
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
