from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'common'

    def ready(self):
        import common.signals
        self._patch_unfold_flatten_context()

    @staticmethod
    def _patch_unfold_flatten_context():
        """
        Patch unfold's _flatten_context to handle non-dict entries in context.dicts.

        Root cause: Django's submit_row() returns a Context object (not a plain dict).
        Django's InclusionNode.render() then calls context.new(Context_object), which
        puts the Context object directly into dicts. When unfold's _flatten_context calls
        context.flatten() on Django 5.0.x, it calls flat.update(Context_object), which
        iterates over the Context (yielding its dicts), and dict.update() fails because
        the first yielded dict is not a 2-tuple.

        The safe fallback (build flat dict by checking hasattr 'd', 'keys') correctly
        skips non-dict entries. unfold uses context.flatten() only on Django >= 5.0,
        but the fix wasn't actually available until Django 5.1.
        """
        try:
            import unfold.templatetags.unfold as unfold_tags

            def _safe_flatten_context(context):
                keys = set()
                for d in context.dicts:
                    if hasattr(d, "keys"):
                        keys.update(d.keys())
                return {k: context[k] for k in keys}

            unfold_tags._flatten_context = _safe_flatten_context
        except ImportError:
            pass
