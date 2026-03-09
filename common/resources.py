from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, DateTimeWidget
from common import models


class TelegramProfileResource(resources.ModelResource):
    created_at = fields.Field(attribute='created_at', column_name='created_at',
                              widget=DateTimeWidget("%m/%d/%Y, %I:%M:%S %p"))
    updated_at = fields.Field(
        attribute="updated_at", column_name="updated_at", widget=DateTimeWidget("%m/%d/%Y, %I:%M:%S %p")
    )

    class Meta:
        model = models.TelegramProfile
        fields = (
            'id',
            'chat_id',
            'username',
            'first_name',
            'lastname',
            'role',
            'created_at',
            'updated_at'
        )
