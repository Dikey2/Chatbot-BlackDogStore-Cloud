from django.contrib import admin

from .models import Business, BusinessDomain, ChatbotConfig, Membership


class DomainInline(admin.TabularInline):
    model = BusinessDomain
    extra = 0


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    raw_id_fields = ["user"]


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "public_id", "is_active", "created_at"]
    search_fields = ["name", "slug"]
    readonly_fields = ["public_id"]
    inlines = [DomainInline, MembershipInline]


admin.site.register(ChatbotConfig)
