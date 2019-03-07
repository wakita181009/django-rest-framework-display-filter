from django.core.exceptions import ImproperlyConfigured
from django.db.models import FieldDoesNotExist
from django.db.models.fields.related import ForeignObjectRel
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.compat import coreapi, coreschema
from rest_framework.filters import BaseFilterBackend


class DisplayFieldFilter(BaseFilterBackend):
    display_param = "display"
    display_fields = None
    display_title = _("Displays")
    display_description = _("Which field to display the results.")

    def filter_queryset(self, request, queryset, view):
        fields = self.get_display(request, queryset, view)
        relations, reverse_relations = self._extract_relations(
            fields, view, {"request": request})
        if relations:
            queryset = queryset.select_related(*relations)
        if reverse_relations:
            queryset = queryset.prefetch_related(*reverse_relations)

        return queryset

    def get_schema_fields(self, view):
        assert coreapi is not None, \
            "coreapi must be installed to use `get_schema_fields()`"
        assert coreschema is not None, \
            "`coreschema` must be installed to use `get_schema_fields()`"
        return [
            coreapi.Field(
                name=self.display_param,
                required=False,
                location="query",
                schema=coreschema.String(
                    title=force_text(self.display_title),
                    description=force_text(self.display_description)
                )
            )
        ]

    def get_display(self, request, queryset, view):
        params = request.query_params.getlist(self.display_param)
        if params:
            fields = [param.strip() for param in params]
            display = self.remove_invalid_fields(
                request, queryset, view, fields
            )
            if display:
                return display

        # No fields was included, or all the fields were invalid
        return getattr(view, "display", None)

    def get_default_valid_fields(self, queryset, view, context):
        serializer_class = self.get_serializer_class(view)
        return [
            (field.source.replace(".", "__") or field_name, field.label)
            for field_name, field in
            serializer_class(context=context).fields.items()
            if (not getattr(field, "write_only", False)
                and not field.source == "*")
        ]

    def get_valid_fields(self, queryset, view, context):
        valid_fields = getattr(view, "display_fields", self.display_fields)

        if valid_fields is None:
            # Default to allowing filtering on serializer fields
            return self.get_default_valid_fields(queryset, view, context)

        elif valid_fields == "__all__":
            # View explicitly allows filtering on any model field
            valid_fields = [
                (field.name, field.verbose_name)
                for field in queryset.model._meta.fields
            ]
            valid_fields += [
                (key, key.title().split("__"))
                for key in queryset.query.annotations
            ]
        else:
            valid_fields = [
                (item, item) if isinstance(item, str) else item
                for item in valid_fields
            ]

        return valid_fields

    def remove_invalid_fields(self, request, queryset, view, fields):
        valid_fields = [item[0] for item in
                        self.get_valid_fields(
                            queryset, view, {"request": request})]
        return [term for term in fields if term in valid_fields]

    def get_serializer_class(self, view):
        # If `ordering_fields` is not specified, then we determine a default
        # based on the serializer class, if one exists on the view.
        if hasattr(view, "get_serializer_class"):
            try:
                serializer_class = view.get_serializer_class()
            except AssertionError:
                # Raised by the default implementation if
                # no serializer_class was found
                serializer_class = None
        else:
            serializer_class = getattr(view, "serializer_class", None)

        if serializer_class is None:
            msg = (
                "Cannot use %s on a view which does not have either a "
                "`serializer_class`, an overriding `get_serializer_class` "
                "or `display_fields` attribute."
            )
            raise ImproperlyConfigured(msg % self.__class__.__name__)

        return serializer_class

    def _extract_relations(self, fields, view, context):
        serializer_class = self.get_serializer_class(view)

        relations, reverse_relations = [], []
        for field_name, field in serializer_class(
                context=context).fields.items():
            if fields and field_name not in fields:
                continue
            try:
                related_field, direct = \
                    self._get_related_field(
                        serializer_class(context=context), field)
            except FieldDoesNotExist:
                continue

            if isinstance(field, serializers.ListSerializer) \
                    and isinstance(field.child, serializers.ModelSerializer):
                reverse_relations.append(field_name)

            if isinstance(field, serializers.ModelSerializer):
                if direct:
                    relations.append(field.source)
                else:
                    reverse_relations.append(field.source)
        return relations, reverse_relations

    @staticmethod
    def _get_related_field(serializer_class, field):
        model_class = serializer_class.Meta.model
        try:
            related_field = model_class._meta.get_field(field.source)
        except FieldDoesNotExist:
            # If `related_name` is not set, field name does not include
            # `_set` -> remove it and check again
            default_postfix = "_set"
            if field.source.endswith(default_postfix):
                related_field = model_class._meta.get_field(
                    field.source[:-len(default_postfix)])
            else:
                raise

        if isinstance(related_field, ForeignObjectRel):
            return related_field.field, False
        return related_field, True
