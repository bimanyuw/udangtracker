from django import forms
from .models import Lot


class LotForm(forms.ModelForm):
    class Meta:
        model = Lot
        # status & risk tidak muncul di form
        fields = ["lot_id", "farm", "harvest_date", "volume_kg", "jenis_kontaminasi"]

        labels = {
            "lot_id": "Lot ID",
            "farm": "Farm",
            "harvest_date": "Harvest date",
            "volume_kg": "Volume (kg)",
            "jenis_kontaminasi": "Jenis kontaminasi (opsional)",
        }

        widgets = {
            "lot_id": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Mis. LOT-2024-001",
                }
            ),
            "farm": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "harvest_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-input",
                }
            ),
            "volume_kg": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "min": "0",
                    "step": "0.1",
                }
            ),
            "jenis_kontaminasi": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Isi jika sudah diketahui",
                }
            ),
        }
