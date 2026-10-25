from django.contrib import admin

from .models import Comment, Floor, Property, Space, SubType, Ticket


class FloorInline(admin.TabularInline):
    model = Floor
    extra = 1


class SpaceInline(admin.TabularInline):
    model = Space
    extra = 1


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ['author', 'created_at']


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    inlines = [FloorInline]
    search_fields = ['name']


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ['name', 'property']
    list_filter = ['property']
    inlines = [SpaceInline]


@admin.register(SubType)
class SubTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'category']
    list_filter = ['category']


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'property', 'category', 'priority', 'status', 'assigned_to', 'complete_by']
    list_filter = ['status', 'priority', 'category', 'property']
    search_fields = ['title', 'description']
    readonly_fields = ['created_by', 'responded_at', 'created_at', 'updated_at']
    inlines = [CommentInline]
