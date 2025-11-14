from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Lot(models.Model):
    lot_id = models.CharField(max_length=100, unique=True)
    creator = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    status = models.CharField(
        max_length=20,
        choices=[
            ("OK", "Aman"),
            ("HOLD", "Ditahan"),
            ("INVESTIGATE", "Investigasi"),
        ],
    )
    jenis_kontaminasi = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.lot_id


class Node(models.Model):
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=100)  # mis: Tambak, Pengumpul, Pabrik

    def __str__(self):
        return self.name


class LotMovement(models.Model):
    lot = models.ForeignKey(
        Lot,
        related_name="movements",
        on_delete=models.CASCADE,
    )
    node = models.ForeignKey(Node, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"{self.lot.lot_id} @ {self.node.name}"
