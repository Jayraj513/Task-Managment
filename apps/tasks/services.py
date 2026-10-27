"""
Task service layer: Dependency graph acyclic validation and task helper services.
"""
from django.core.exceptions import ValidationError


def detect_dependency_cycle(predecessor_id, successor_id, TaskDependencyModel):
    """
    Check if adding an edge (predecessor_id -> successor_id) creates a cycle
    in the directed dependency graph.
    Returns True if a cycle would be created, False otherwise.
    """
    if predecessor_id == successor_id:
        return True

    # Breadth-first search / Depth-first search starting from successor_id:
    # If predecessor_id is reachable from successor_id, adding (pred -> succ) creates a cycle!
    visited = set()
    queue = [successor_id]

    while queue:
        curr = queue.pop(0)
        if curr == predecessor_id:
            return True
        if curr not in visited:
            visited.add(curr)
            # Find all tasks that depend on curr (where curr is the predecessor)
            next_tasks = TaskDependencyModel.objects.filter(
                predecessor_task_id=curr
            ).values_list('successor_task_id', flat=True)
            for nxt in next_tasks:
                if nxt not in visited:
                    queue.append(nxt)

    return False


def validate_dependency(predecessor_task, successor_task, TaskDependencyModel, instance_pk=None):
    """
    Validates that a dependency does not link a task to itself
    and does not introduce a cyclic dependency.
    """
    if predecessor_task.id == successor_task.id:
        raise ValidationError('A task cannot depend on itself.')

    if predecessor_task.project_id != successor_task.project_id:
        # Cross project dependency check if desired, but we can allow within workspace
        if predecessor_task.project.workspace_id != successor_task.project.workspace_id:
            raise ValidationError('Tasks must belong to the same workspace.')

    # Check for direct inverse dependency
    if TaskDependencyModel.objects.filter(
        predecessor_task=successor_task,
        successor_task=predecessor_task
    ).exists():
        raise ValidationError(
            f"Cannot create dependency: '{successor_task.title}' already depends on '{predecessor_task.title}' (circular dependency)."
        )

    # Check for multi-node cycle
    # Exclude current instance if editing
    existing_qs = TaskDependencyModel.objects.all()
    if instance_pk:
        existing_qs = existing_qs.exclude(pk=instance_pk)

    if detect_dependency_cycle(predecessor_task.id, successor_task.id, TaskDependencyModel):
        raise ValidationError(
            f"Cannot add dependency: creates a circular dependency loop between '{predecessor_task.title}' and '{successor_task.title}'."
        )
