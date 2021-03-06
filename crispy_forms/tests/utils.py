__all__ = ('override_settings', 'setup')


try:
    from django import setup
except ImportError:
    def setup():
        pass


try:
    from django.test.runner import DiscoverRunner
except ImportError:
    # Django 1.5 or earlier. Fallback to a patched version of the old runner.
    # Should be removed when dropping 1.4 and 1.5 support.
    from django.test.simple import DjangoTestSuiteRunner

    class DiscoverRunner(DjangoTestSuiteRunner):
        def run_tests(self, tests, *args, **kwargs):
            tests = [
                test.replace('crispy_forms.tests.', 'crispy_forms.')
                for test in tests
            ]
            return super(DiscoverRunner, self).run_tests(tests, *args, **kwargs)


try:
    from django.template import engines

    def get_template_from_string(s):
        return engines['django'].from_string(s)

except ImportError:
    # Old template loading private API in Django < 1.8.
    # Remove this when dropping 1.4 and 1.7 support.
    from django.template import loader

    def get_template_from_string(s):
        return loader.get_template_from_string(s)


try:
    from django.test.utils import override_settings
except ImportError:
    # we are in Django 1.3
    from django.conf import settings, UserSettingsHolder
    from django.utils.functional import wraps

    class override_settings(object):
        """
        Acts as either a decorator, or a context manager. If it's a decorator
        it takes a function and returns a wrapped function. If it's a
        contextmanager it's used with the ``with`` statement. In either event
        entering/exiting are called before and after, respectively,
        the function/block is executed.

        This class was backported from Django 1.5

        As django.test.signals.setting_changed is not supported in 1.3,
        it's not sent on changing settings.
        """
        def __init__(self, **kwargs):
            self.options = kwargs
            self.wrapped = settings._wrapped

        def __enter__(self):
            self.enable()

        def __exit__(self, exc_type, exc_value, traceback):
            self.disable()

        def __call__(self, test_func):
            from django.test import TransactionTestCase
            if isinstance(test_func, type):
                if not issubclass(test_func, TransactionTestCase):
                    raise Exception(
                        "Only subclasses of Django SimpleTestCase "
                        "can be decorated with override_settings")
                original_pre_setup = test_func._pre_setup
                original_post_teardown = test_func._post_teardown

                def _pre_setup(innerself):
                    self.enable()
                    original_pre_setup(innerself)

                def _post_teardown(innerself):
                    original_post_teardown(innerself)
                    self.disable()
                test_func._pre_setup = _pre_setup
                test_func._post_teardown = _post_teardown
                return test_func
            else:
                @wraps(test_func)
                def inner(*args, **kwargs):
                    with self:
                        return test_func(*args, **kwargs)
            return inner

        def enable(self):
            override = UserSettingsHolder(settings._wrapped)
            for key, new_value in self.options.items():
                setattr(override, key, new_value)
            settings._wrapped = override

        def disable(self):
            settings._wrapped = self.wrapped
