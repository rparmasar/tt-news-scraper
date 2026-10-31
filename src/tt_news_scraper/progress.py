from rich.progress import track, Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn


class FetchingProgress:
    """Context manager for tracking fetching operations."""

    def __init__(self, total=None, description="Fetching..."):
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
        )
        self.tasks = {}
        self.total = total

    def __enter__(self):
        self.progress.start()
        return self

    def __exit__(self, *args):
        self.progress.stop()

    def add_task(self, name: str, total=None) -> int:
        """Register a task and return its ID."""
        if hasattr(total, "__len__") and callable(getattr(total, "__call__", False)):
            total = len(total)

        task_id = self.progress.add_task(
            f"[cyan]{name}",
            total=total or 1,
            start=False,
        )
        return task_id

    def update(self, task_id: int, advance: float | None = None):
        """Update progress by N items."""
        if advance is not None:
            self.progress.update(task_id, advance=advance)

    def finish_task(self, task_id: int):
        """Mark a task as complete."""
        self.progress.update(task_id, completed=True)
