from django.db import models
from django.contrib.auth.models import User # Kita pakai User bawaan Django

# MASTER DATA: Titik-titik di Rantai Pasok
class Node(models.Model):
    NODE_TYPES = [
        ('TAMBAK', 'Tambak'),
        ('PENGUMPUL', 'Pengumpul'),
        ('PABRIK', 'Pabrik Pengolahan'),
        ('EKSPORTIR', 'Eksportir'),
    ]
    
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=NODE_TYPES)
    location = models.CharField(max_length=255, blank=True) # Opsional

    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"

# DATA UTAMA: Lot Udang
class Lot(models.Model):
    STATUS_CHOICES = [
        ('OK', 'OK'),
        ('HOLD', 'Ditahan'),
        ('INVESTIGATE', 'Investigasi'),
    ]
    
    lot_id = models.CharField(max_length=50, unique=True, help_text="ID Unik Lot, misal: A-001")
    # 'creator' bisa di-link ke User Petambak
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="lots_created")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OK')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.lot_id

# DATA TRANSAKSI: Mencatat Pergerakan Lot
class LotMovement(models.Model):
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name="movements")
    node_from = models.ForeignKey(Node, on_delete=models.SET_NULL, null=True, blank=True, related_name="departures")
    node_to = models.ForeignKey(Node, on_delete=models.PROTECT, related_name="arrivals")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.lot.lot_id} tiba di {self.node_to.name}"

# DATA TRANSAKSI: Mencatat Hasil Uji Kualitas
# tracker/models.py

class QCResult(models.Model):
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name="qc_results")
    node_at = models.ForeignKey(Node, on_delete=models.PROTECT, help_text="Diuji di node mana")
    metric_name = models.CharField(max_length=100, help_text="Contoh: Cesium")
    metric_value = models.FloatField()
    unit = models.CharField(max_length=20, default="mg/kg")

    # ➕ Tambahan untuk deteksi kontaminasi
    limit_value = models.FloatField(
        null=True,
        blank=True,
        help_text="Batas maksimum yang diizinkan (opsional)"
    )
    is_contaminated = models.BooleanField(
        default=False,
        help_text="True jika nilai melewati batas"
    )

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Uji {self.metric_name} untuk {self.lot.lot_id}"

    def save(self, *args, **kwargs):
        # Kalau ada limit_value, otomatis tentukan apakah contaminated
        if self.limit_value is not None:
            self.is_contaminated = self.metric_value > self.limit_value

            # Kalau contaminated, otomatis ubah status lot jadi INVESTIGATE
            if self.is_contaminated and self.lot.status == "OK":
                self.lot.status = "INVESTIGATE"
                self.lot.save()

        super().save(*args, **kwargs)
