"""
Background task queue using FastAPI's built-in BackgroundTasks.

Each task function is a plain Python callable that FastAPI runs in a
thread pool after the HTTP response is sent.

Upgrade path to Celery/RQ:
  1. Replace @task_registry.register with @celery_app.task
  2. Call task.delay(**kwargs) instead of background_tasks.add_task(fn, **kwargs)
  3. All functions here are designed to be drop-in compatible.
"""
from typing import Any
from tax_capsule.utils.logger import get_logger
from documents.pdf_filler import fill_form_pdf
from documents.vault import store_document

logger = get_logger("Tasks")


def generate_and_store_document(
    record_id: int,
    doc_type: str,
    fmt: str,
    form_data: dict[str, Any],
    user_id: int,
) -> None:
    """
    Background task: generate a document from pre-computed form_data
    and store it in the document vault.
    Runs after the HTTP response is returned to the caller.
    """
    try:
        if fmt == "pdf":
            content = fill_form_pdf(form_data)
        elif fmt == "json":
            import json
            content = json.dumps(form_data, default=str, indent=2).encode()
        elif fmt == "xml":
            from documents.xml_efile import generate_1120_xml, generate_1065_xml
            generators = {"1120": generate_1120_xml, "1065": generate_1065_xml}
            if doc_type not in generators:
                logger.error(f"No XML generator for doc_type={doc_type}")
                return
            content = generators[doc_type](form_data).encode()
        else:
            logger.error(f"Unknown fmt={fmt} in generate_and_store_document")
            return

        meta = store_document(record_id, doc_type, fmt, content)
        logger.info(
            f"Background task completed: record={record_id} doc_type={doc_type} "
            f"fmt={fmt} size={meta['size_bytes']}B"
        )
    except Exception as e:
        logger.error(
            f"Background task failed: record={record_id} doc_type={doc_type}: {e}",
            exc_info=True,
        )


def sync_managerio_background(entity_name: str) -> None:
    """Background task: pull Manager.io data and log results."""
    try:
        from manager_sync_agent.sync_managerio import pull_managerio_data
        result = pull_managerio_data()
        logger.info(
            f"Managerio background sync for '{entity_name}': "
            f"{result.get('record_count', 0)} records"
        )
    except Exception as e:
        logger.error(f"Background Managerio sync failed: {e}")


def invalidate_record_cache(record_id: int) -> None:
    """Background task: evict all cache keys for a given record."""
    try:
        from app.cache import cache_clear_prefix
        deleted = cache_clear_prefix(f"record:{record_id}:")
        logger.info(f"Cache invalidation: record={record_id}, {deleted} keys evicted")
    except Exception as e:
        logger.error(f"Cache invalidation failed for record {record_id}: {e}")
