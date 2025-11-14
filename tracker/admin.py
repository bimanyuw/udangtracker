from django.contrib import admin
from .models import Node, Lot, LotMovement


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ("name", "type")
    search_fields = ("name", "type")


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ("lot_id", "creator", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("lot_id", "creator__username")


@admin.register(LotMovement)
class LotMovementAdmin(admin.ModelAdmin):
    list_display = ("lot", "node", "timestamp")
    list_filter = ("node", "timestamp")
    search_fields = ("lot__lot_id", "node__name")
