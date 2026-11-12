#!/usr/bin/env python3
"""Topological sorting utilities for task dependencies.

This module extracts topological sort logic from orchestrator.py
into a separate module for better separation of concerns.
"""


def topological_sort_subtasks(sub_tasks: list[dict]) -> list[list[dict]]:
    """Sorts sub_tasks topologically based on their depends_on field.

    Returns a list of waves (lists of tasks that can be run concurrently).

    Args:
        sub_tasks: List of task dictionaries with 'id' and 'depends_on' fields.

    Returns:
        List of waves, where each wave is a list of tasks that can run concurrently.
    """
    id_to_task = {t["id"]: t for t in sub_tasks}

    # Calculate in-degree and adjacency list
    in_degree = {t["id"]: 0 for t in sub_tasks}
    adj = {t["id"]: [] for t in sub_tasks}

    for t in sub_tasks:
        for dep in t.get("depends_on", []):
            if dep in id_to_task:
                adj[dep].append(t["id"])
                in_degree[t["id"]] += 1
            else:
                # Dependency not found, ignore
                pass

    # Find all tasks with 0 in-degree
    queue = [t["id"] for t in sub_tasks if in_degree[t["id"]] == 0]
    waves = []

    while queue:
        current_wave_ids = list(queue)
        queue = []
        wave_tasks = []
        for u in current_wave_ids:
            wave_tasks.append(id_to_task[u])
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)
        waves.append(wave_tasks)

    # Check for cycles / unvisited nodes
    flat_sorted = [t["id"] for wave in waves for t in wave]
    if len(flat_sorted) < len(sub_tasks):
        unvisited = [t for t in sub_tasks if t["id"] not in flat_sorted]
        if unvisited:
            waves.append(unvisited)

    return waves
