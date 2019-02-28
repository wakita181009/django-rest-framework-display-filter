class DisplayFieldMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and hasattr(request, "query_params"):
            fields = request.query_params.getlist("display")
            if fields:
                for field_name in set(self.fields.keys()) - set(fields):
                    self.fields.pop(field_name)
