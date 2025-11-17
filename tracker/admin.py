from django.contrib import admin
from .models import (
    Lot,
    Node,
    LotMovement,
    Farm,
    PondLog,
    Sampling,
    LabTest,
    Document,
    Incident,
    IncidentRelatedLot,
)


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ("lot_id", "farm", "status", "risk_level", "risk_score", "created_at")
    list_filter = ("status", "risk_level", "farm")
    search_fields = ("lot_id",)


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ("name", "type")
    list_filter = ("type",)
    search_fields = ("name",)


@admin.register(LotMovement)
class LotMovementAdmin(admin.ModelAdmin):
    list_display = ("lot", "node", "timestamp", "location", "quantity_kg")
    list_filter = ("node__type",)
    search_fields = ("lot__lot_id", "node__name")


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "owner_name")
    search_fields = ("name", "location", "owner_name")


@admin.register(PondLog)
class PondLogAdmin(admin.ModelAdmin):
    list_display = ("farm", "date", "ph", "temperature_c", "salinity_ppt")
    list_filter = ("farm", "date")


@admin.register(Sampling)
class SamplingAdmin(admin.ModelAdmin):
    list_display = ("lot", "date", "location", "status")
    list_filter = ("status", "date")
    search_fields = ("lot__lot_id",)


@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ("sampling", "parameter", "value", "unit", "result")
    list_filter = ("parameter", "result")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "doc_type", "farm", "lot", "issue_date", "expiry_date")
    list_filter = ("doc_type", "farm")
    search_fields = ("title",)


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("lot", "incident_type", "status", "date")
    list_filter = ("incident_type", "status")
    search_fields = ("lot__lot_id",)


@admin.register(IncidentRelatedLot)
class IncidentRelatedLotAdmin(admin.ModelAdmin):
    list_display = ("incident", "lot")
