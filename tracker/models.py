from django.db import models
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

User = get_user_model()


# =========================
# Node & Farm (Tambak)
# =========================

class Node(models.Model):
    NODE_TYPE_CHOICES = [
        ("FARM", "Tambak / Farm"),
        ("COLLECTOR", "Pengumpul"),
        ("PROCESSOR", "Pabrik / Processor"),
        ("EXPORTER", "Eksportir"),
    ]

    name = models.CharField(max_length=100)
    type = models.CharField(
        max_length=20,
        choices=NODE_TYPE_CHOICES,
    )  # mis: Tambak, Pengumpul, Pabrik, Eksportir

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class Farm(models.Model):
    """
    Profil khusus untuk tambak.
    Bisa di-link ke Node dengan type=FARM (optional).
    """
    node = models.OneToOneField(
        Node,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="farm_profile",
    )
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True)
    owner_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


# =========================
# Lot & Pergerakan Lot
# =========================

class Lot(models.Model):
    # status KONTAMINASI / TINDAKAN (punyamu tadi)
    CONTAM_STATUS_CHOICES = [
        ("OK", "Aman"),
        ("HOLD", "Ditahan"),
        ("INVESTIGATE", "Investigasi"),
    ]

    # level risiko (buat dashboard & badge warna)
    RISK_LEVEL_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
    ]

    lot_id = models.CharField(max_length=100, unique=True)
    creator = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    # tambahkan info basic lot
    farm = models.ForeignKey(
        Farm,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lots",
    )
    harvest_date = models.DateField(null=True, blank=True)
    volume_kg = models.FloatField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=CONTAM_STATUS_CHOICES,
        default="OK",
    )
    jenis_kontaminasi = models.CharField(max_length=100, blank=True, null=True)

    # risk score (buat fitur risk scoring)
    risk_score = models.IntegerField(default=0)
    risk_level = models.CharField(
        max_length=10,
        choices=RISK_LEVEL_CHOICES,
        default="LOW",
    )

    # buat QR / public view
    public_token = models.CharField(
        max_length=32,
        unique=True,
        blank=True,
        null=True,  
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.public_token:
            self.public_token = get_random_string(24)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.lot_id


class LotMovement(models.Model):
    """
    Chain-of-custody: lot berpindah dari satu Node ke Node lain.
    """
    lot = models.ForeignKey(
        Lot,
        related_name="movements",
        on_delete=models.CASCADE,
    )
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    # optional: info tambahan
    location = models.CharField(max_length=200, blank=True)
    quantity_kg = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.lot.lot_id} @ {self.node.name}"


# =========================
# Log Tambak (PondLog)
# =========================

class PondLog(models.Model):
    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name="pond_logs",
    )
    date = models.DateField()
    ph = models.FloatField(null=True, blank=True)
    temperature_c = models.FloatField(null=True, blank=True)
    salinity_ppt = models.FloatField(null=True, blank=True)
    feed_type = models.CharField(max_length=100, blank=True)
    chemicals_used = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"Log {self.farm.name} - {self.date}"


# =========================
# Sampling & Hasil Uji Lab
# =========================

class Sampling(models.Model):
    lot = models.ForeignKey(
        Lot,
        on_delete=models.CASCADE,
        related_name="samplings",
    )
    date = models.DateField()
    location = models.CharField(max_length=200, blank=True)
    requested_by = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("PLANNED", "Planned"),
            ("SAMPLED", "Sampled"),
            ("SENT_TO_LAB", "Sent to Lab"),
        ],
        default="PLANNED",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sampling {self.lot.lot_id} - {self.date}"


class LabTest(models.Model):
    RESULT_CHOICES = [
        ("PASS", "Pass"),
        ("FAIL", "Fail"),
    ]

    sampling = models.ForeignKey(
        Sampling,
        on_delete=models.CASCADE,
        related_name="tests",
    )
    parameter = models.CharField(max_length=100)  # contoh: Cesium, Pb, Cd, TPC
    value = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=20, blank=True)
    limit_value = models.FloatField(null=True, blank=True)
    result = models.CharField(
        max_length=10,
        choices=RESULT_CHOICES,
        default="PASS",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.parameter} ({self.result}) for {self.sampling.lot.lot_id}"


# =========================
# Dokumen & Sertifikasi
# =========================

class Document(models.Model):
    DOC_TYPE_CHOICES = [
        ("LAB_CERT", "Sertifikat Lab"),
        ("FARM_CERT", "Sertifikat Tambak"),
        ("EXPORT_DOC", "Dokumen Ekspor"),
        ("OTHER", "Lainnya"),
    ]

    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="documents/", blank=True, null=True)

    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documents",
    )
    lot = models.ForeignKey(
        Lot,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documents",
    )

    issued_by = models.CharField(max_length=100, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# =========================
# Insiden & Investigasi
# =========================

class Incident(models.Model):
    INCIDENT_TYPE_CHOICES = [
        ("EXPORT_REJECT", "Penolakan Ekspor"),
        ("LAB_FAIL", "Gagal Uji"),
        ("COMPLAINT", "Keluhan Buyer"),
    ]
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In Progress"),
        ("CLOSED", "Closed"),
    ]

    lot = models.ForeignKey(
        Lot,
        on_delete=models.CASCADE,
        related_name="incidents",
    )
    incident_type = models.CharField(max_length=20, choices=INCIDENT_TYPE_CHOICES)
    description = models.TextField()
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="OPEN")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_incident_type_display()} - {self.lot.lot_id}"


class IncidentRelatedLot(models.Model):
    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name="related_lots",
    )
    lot = models.ForeignKey(
        Lot,
        on_delete=models.CASCADE,
        related_name="related_incidents",
    )

    def __str__(self):
        return f"{self.incident.id} ↔ {self.lot.lot_id}"
