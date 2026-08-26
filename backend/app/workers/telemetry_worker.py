from app.workers.celery_app import celery_app

@celery_app.task
def process_telemetry(measurement_id: int):
    # Perform post-processing, e.g., check thresholds, trigger alerts
    pass