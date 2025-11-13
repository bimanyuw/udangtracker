# tracker/admin.py

from django.contrib import admin
from .models import Node, Lot, LotMovement, QCResult


class LotMovementInline(admin.TabularInline):
    model = LotMovement
    extra = 1
    autocomplete_fields = ['node_from', 'node_to']


class QCResultInline(admin.TabularInline):
    model = QCResult
    extra = 1
    autocomplete_fields = ['node_at']


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'location')
    list_filter = ('type',)
    search_fields = ('name', 'location')


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ('lot_id', 'creator', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('lot_id', 'creator__username')
    inlines = [LotMovementInline, QCResultInline]


@admin.register(LotMovement)
class LotMovementAdmin(admin.ModelAdmin):
    list_display = ('lot', 'node_from', 'node_to', 'timestamp')
    list_filter = ('node_from', 'node_to')
    autocomplete_fields = ['lot', 'node_from', 'node_to']


@admin.register(QCResult)
class QCResultAdmin(admin.ModelAdmin):
    list_display = (
        'lot',
        'node_at',
        'metric_name',
        'metric_value',
        'unit',
        'limit_value',
        'is_contaminated',
        'timestamp',
    )
    list_filter = ('metric_name', 'node_at', 'is_contaminated')
    search_fields = ('lot__lot_id', 'metric_name')
    autocomplete_fields = ['lot', 'node_at']
