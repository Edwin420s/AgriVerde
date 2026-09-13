try:
    from celery import Celery
    from app.core.config import settings

    celery_app = Celery("agriverde", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )
except ImportError:
    class DummyCelery:
        def task(self, *args, **kwargs):
            def decorator(f):
                class DummyTask:
                    def __init__(self, fn):
                        self.fn = fn
                    def __call__(self, *a, **kw):
                        return self.fn(*a, **kw)
                    def delay(self, *a, **kw):
                        return None
                return DummyTask(f)
            if len(args) == 1 and callable(args[0]):
                return decorator(args[0])
            return decorator

    celery_app = DummyCelery()