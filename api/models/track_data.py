from typing import Iterable
from django.db.models.signals import post_init


def track_data(*fields: Iterable[str]):
    """
    Tracks property changes on a model instance.
    This uses Django's post_init to save a copy of the original field names passed in.

    The changed list of properties is refreshed on model initialization
    and save.

    Adds functions to class model:
    `has_changed(field: str)`, `old_value(field: str)`, `whats_changed()`
    Thank you: https://cra.mr/2010/12/06/tracking-changes-to-fields-in-django

    >>> @track_data('name')
    >>> class Post(models.Model):
    >>>     name = models.CharField(...)
    >>>
    >>>     @classmethod
    >>>     def post_save(cls, sender, instance, created, **kwargs):
    >>>         if instance.has_changed('name'):
    >>>             print "Hooray!"
    """

    UNSAVED = dict()

    def _store(self):
        "Updates a local copy of attributes values"
        if self.id:
            self.__data = dict((f, getattr(self, f)) for f in fields)
        else:
            self.__data = UNSAVED

    def inner(cls):
        # contains a local copy of the previous values of attributes
        cls.__data = {}

        def set_tracked_data(self, data: dict):
            """Set the data for the model instance.
            Use this if you want to manually set some key, value original data.

            Args:
                data (dict): The data to set.
            """
            for k, v in data.items():
                self.__data[k] = v
            # self.__data = data
        cls.set_tracked_data = set_tracked_data

        def has_changed(self, field: str):
            "Returns ``True`` if ``field`` has changed since initialization."
            if self.__data is UNSAVED:
                return False
            return self.__data.get(field) != getattr(self, field)
        cls.has_changed = has_changed

        def old_value(self, field: str):
            "Returns the previous value of ``field``"
            return self.__data.get(field)
        cls.old_value = old_value

        def whats_changed(self) -> dict:
            "Returns a list of changed attributes."
            changed = {}
            if self.__data is UNSAVED:
                return changed
            for k, v in self.__data.items():
                if v != getattr(self, k):
                    changed[k] = v
            return changed
        cls.whats_changed = whats_changed

        # Ensure we are updating local attributes on model init
        def _post_init(sender, instance, **kwargs):
            _store(instance)
        post_init.connect(_post_init, sender=cls, weak=False)

        # Ensure we are updating local attributes on model save
        def save(self, *args, **kwargs):
            save._original(self, *args, **kwargs)
            _store(self)
        save._original = cls.save
        cls.save = save
        return cls
    return inner
