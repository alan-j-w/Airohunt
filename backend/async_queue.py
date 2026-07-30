import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, Awaitable, List

class JobTask:
    def __init__(self, task_id: str, name: str = "Job Scrape Task"):
        self.task_id = task_id
        self.name = name
        self.status = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
        self.progress = 0.0      # 0.0 to 100.0
        self.status_message = "Task queued"
        self.result = None
        self.error = None
        now_str = datetime.now(timezone.utc).isoformat()
        self.created_at = now_str
        self.updated_at = now_str
        self._asyncio_task: Optional[asyncio.Task] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status,
            "progress": round(self.progress, 1),
            "status_message": self.status_message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

class AsyncJobTaskQueue:
    """
    In-memory async task queue manager for job scraping, batch hydration,
    and heavy deduplication operations.
    """
    def __init__(self):
        self._tasks: Dict[str, JobTask] = {}

    def create_task(self, name: str = "Job Task") -> JobTask:
        task_id = str(uuid.uuid4())
        task = JobTask(task_id, name)
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[JobTask]:
        return self._tasks.get(task_id)

    def update_progress(self, task_id: str, progress: float, message: str = ""):
        task = self._tasks.get(task_id)
        if task:
            task.progress = min(max(progress, 0.0), 100.0)
            if message:
                task.status_message = message
            task.updated_at = datetime.now(timezone.utc).isoformat()

    def dispatch_background_task(self, name: str, coro_fn: Callable[..., Awaitable[Any]], *args, **kwargs) -> JobTask:
        """Dispatches an async coroutine function as a tracked background task."""
        task = self.create_task(name)
        task.status = "RUNNING"
        task.status_message = "Task started"

        async def runner():
            try:
                res = await coro_fn(task.task_id, *args, **kwargs)
                task.status = "COMPLETED"
                task.progress = 100.0
                task.status_message = "Task completed successfully"
                task.result = res
            except Exception as e:
                task.status = "FAILED"
                task.status_message = f"Task failed: {str(e)}"
                task.error = str(e)
            finally:
                task.updated_at = datetime.now(timezone.utc).isoformat()

        asyncio_task = asyncio.create_task(runner())
        task._asyncio_task = asyncio_task
        return task

    def list_active_tasks(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._tasks.values()]

# Global singleton task queue instance
global_job_task_queue = AsyncJobTaskQueue()
