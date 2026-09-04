from django import template

register = template.Library()


@register.filter
def filter_status(queryset, status):
    """Filter security cheques by status. Works with both querysets and lists."""
    from django.db.models import QuerySet
    # Check if it's a list (not a queryset)
    if isinstance(queryset, list):
        return [item for item in queryset if item.status == status]
    # It's a QuerySet - always convert to list first to avoid sliced queryset issues
    if isinstance(queryset, QuerySet):
        return [item for item in queryset if item.status == status]
    # Fallback for other iterables
    return [item for item in queryset if item.status == status]


@register.filter
def document_type(queryset, doc_type):
    """Filter documents by document_type. Works with both querysets and lists."""
    # Check if it's a list (not a queryset)
    if isinstance(queryset, list):
        return [item for item in queryset if item.document_type == doc_type]
    # It's a queryset, but check if it's been sliced (evaluated)
    if hasattr(queryset, '_result_cache') and queryset._result_cache is not None:
        return [item for item in queryset if item.document_type == doc_type]
    # It's an unevaluated queryset
    return queryset.filter(document_type=doc_type)


@register.filter
def exists(queryset):
    """Check if queryset has any results."""
    if isinstance(queryset, list):
        return len(queryset) > 0
    if hasattr(queryset, '_result_cache') and queryset._result_cache is not None:
        return len(queryset) > 0
    return queryset.exists()