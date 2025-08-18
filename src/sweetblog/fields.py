# sweetblog/fields.py
from django.db import models


class MarkdownField(models.TextField):
    """TextField that uses the split-pane MarkdownWidget in forms/admin."""
    description = "Markdown text (stored as plain text)"

    def formfield(self, **kwargs):
        from sweetblog.widgets import MarkdownWidget

        defaults = {"widget": MarkdownWidget(attrs={
                'class': 'form-control markdown-content-editor',
                'placeholder': 'Write your article content in Markdown format'
            })}
        defaults.update(kwargs)
        return super().formfield(**defaults)
