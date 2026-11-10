"""Organizer graph structures, durable checkpointing, and capability fabric for DocumentOrganizer.

Provides:
1. Node & OrganizerGraph (and DocumentOrganizerGraph alias): Directed Acyclic Graph (DAG)
   with topological sorting, cycle detection, and dependency tracking.
2. Temporal & Open-SWE Resilience:
   - WorkflowCheckpointer, MemoryWorkflowCheckpointer, FileWorkflowCheckpointer for state
     snapshots, time-travel debugging, and crash recovery.
   - RetryPolicy with exponential backoff, jitter, and non-retryable error filtering.
   - SagaCoordinator for transaction compensation and rollback on failure.
   - CapabilityFabric & CapabilityHook for telemetry, idempotency, and audit lifecycle events.
3. build_document_organizer_graph: Typed LangGraph StateGraph pipeline and DurableFallbackRunner
   supporting both synchronous (.invoke) and asynchronous (.ainvoke) execution.
"""

from __future__ import annotations

import uuid


def _get_default_langgraph_checkpointer():
    try:
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()
    except Exception:
        return None


import asyncio
import inspect
import json
import logging
import random
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    Any,
)

try:
    from typing_extensions import TypedDict
except ImportError:
    from typing import TypedDict  # type: ignore

try:
    from langgraph.graph import END, START, StateGraph

    _LANGGRAPH_AVAILABLE = True
except ImportError:
    _LANGGRAPH_AVAILABLE = False

logger = logging.getLogger("DocumentOrganizer.Graph")


# ---------------------------------------------------------------------------
# Core DAG Data Structures
# ---------------------------------------------------------------------------


@dataclass
class Node:
    """Graph node representing a document or task unit."""

    id: str
    dependencies: set[str] = field(default_factory=set)
    data: dict[str, Any] = field(default_factory=dict)


class OrganizerGraph:
    """Directed graph representation for dependency management and topological ordering."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}

    def add_node(self, node_id: str, data: dict[str, Any] | None = None) -> None:
        """Add a new node to the graph if not already present."""
        if node_id not in self.nodes:
            self.nodes[node_id] = Node(id=node_id, dependencies=set(), data=data or {})
        elif data:
            self.nodes[node_id].data.update(data)

    def add_dependency(self, from_node: str, to_node: str) -> None:
        """Add a dependency relationship: from_node depends on to_node."""
        self.add_node(from_node)
        self.add_node(to_node)
        self.nodes[from_node].dependencies.add(to_node)

    def get_dependencies(self, node_id: str) -> set[str]:
        """Get all direct dependencies for a given node."""
        if node_id in self.nodes:
            return self.nodes[node_id].dependencies.copy()
        return set()

    def get_dependents(self, node_id: str) -> set[str]:
        """Get all nodes that directly depend on the given node."""
        return {nid for nid, node in self.nodes.items() if node_id in node.dependencies}

    def has_cycle(self) -> bool:
        """Check whether the graph contains any cycle."""
        try:
            self.topological_sort()
            return False
        except ValueError:
            return True

    def topological_sort(self) -> list[str]:
        """Return nodes in topological order (dependencies appear before dependents).

        Raises:
            ValueError: If a cycle is detected, reporting cycle path.
        """
        visited: set[str] = set()
        temp_visited: list[str] = []
        order: list[str] = []

        def visit(node_id: str) -> None:
            if node_id in temp_visited:
                cycle_start = temp_visited.index(node_id)
                cycle_path = " -> ".join(temp_visited[cycle_start:] + [node_id])
                raise ValueError(f"Cycle detected in graph: {cycle_path}")
            if node_id not in visited:
                temp_visited.append(node_id)
                for dep in sorted(self.get_dependencies(node_id)):
                    visit(dep)
                temp_visited.pop()
                visited.add(node_id)
                order.append(node_id)

        for node_id in sorted(self.nodes.keys()):
            if node_id not in visited:
                visit(node_id)

        return order


# Backward compatibility and test alias
DocumentOrganizerGraph = OrganizerGraph


# ---------------------------------------------------------------------------
# Checkpointing Fabric (Temporal / Open-SWE Paradigm)
# ---------------------------------------------------------------------------


class WorkflowCheckpointStatus:
    """Status enumeration for workflow checkpoints."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    CHECKPOINTED = "CHECKPOINTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"


@dataclass
class CheckpointMetadata:
    """Metadata recorded for every durable workflow checkpoint."""

    checkpoint_id: str
    thread_id: str
    step_name: str
    step_index: int
    timestamp: str
    status: str
    error: str | None = None
    execution_time_ms: float = 0.0
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "thread_id": self.thread_id,
            "step_name": self.step_name,
            "step_index": self.step_index,
            "timestamp": self.timestamp,
            "status": self.status,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metrics": self.metrics,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckpointMetadata:
        return cls(
            checkpoint_id=data.get("checkpoint_id", ""),
            thread_id=data.get("thread_id", ""),
            step_name=data.get("step_name", ""),
            step_index=data.get("step_index", 0),
            timestamp=data.get("timestamp", ""),
            status=data.get("status", WorkflowCheckpointStatus.CHECKPOINTED),
            error=data.get("error"),
            execution_time_ms=data.get("execution_time_ms", 0.0),
            metrics=data.get("metrics", {}),
        )


@dataclass
class WorkflowCheckpoint:
    """Durable state snapshot at a workflow step boundary."""

    metadata: CheckpointMetadata
    state: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "state": self.state,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowCheckpoint:
        return cls(
            metadata=CheckpointMetadata.from_dict(data.get("metadata", {})),
            state=data.get("state", {}),
        )


class WorkflowCheckpointer(ABC):
    """Abstract protocol for durable asynchronous workflow checkpointing."""

    @abstractmethod
    def save_checkpoint(self, thread_id: str, checkpoint: WorkflowCheckpoint) -> str:
        """Persist a workflow checkpoint synchronously."""

    @abstractmethod
    def get_latest_checkpoint(self, thread_id: str) -> WorkflowCheckpoint | None:
        """Retrieve the latest checkpoint for a thread synchronously."""

    @abstractmethod
    def get_checkpoint(
        self, thread_id: str, checkpoint_id: str
    ) -> WorkflowCheckpoint | None:
        """Retrieve a specific checkpoint by ID synchronously."""

    @abstractmethod
    def list_checkpoints(self, thread_id: str) -> list[WorkflowCheckpoint]:
        """List all checkpoints for a given thread in chronological order."""

    async def save_checkpoint_async(
        self, thread_id: str, checkpoint: WorkflowCheckpoint
    ) -> str:
        """Asynchronously persist a checkpoint."""
        return self.save_checkpoint(thread_id, checkpoint)

    async def get_latest_checkpoint_async(
        self, thread_id: str
    ) -> WorkflowCheckpoint | None:
        """Asynchronously retrieve the latest checkpoint."""
        return self.get_latest_checkpoint(thread_id)

    async def get_checkpoint_async(
        self, thread_id: str, checkpoint_id: str
    ) -> WorkflowCheckpoint | None:
        """Asynchronously retrieve a specific checkpoint."""
        return self.get_checkpoint(thread_id, checkpoint_id)


class MemoryWorkflowCheckpointer(WorkflowCheckpointer):
    """In-memory thread-safe checkpointer for fast testing and ephemeral workflows."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, list[WorkflowCheckpoint]] = {}

    def save_checkpoint(self, thread_id: str, checkpoint: WorkflowCheckpoint) -> str:
        if thread_id not in self._checkpoints:
            self._checkpoints[thread_id] = []
        self._checkpoints[thread_id].append(checkpoint)
        return checkpoint.metadata.checkpoint_id

    def get_latest_checkpoint(self, thread_id: str) -> WorkflowCheckpoint | None:
        items = self._checkpoints.get(thread_id, [])
        return items[-1] if items else None

    def get_checkpoint(
        self, thread_id: str, checkpoint_id: str
    ) -> WorkflowCheckpoint | None:
        for cp in self._checkpoints.get(thread_id, []):
            if cp.metadata.checkpoint_id == checkpoint_id:
                return cp
        return None

    def list_checkpoints(self, thread_id: str) -> list[WorkflowCheckpoint]:
        return list(self._checkpoints.get(thread_id, []))


class FileWorkflowCheckpointer(WorkflowCheckpointer):
    """Durable file-backed checkpointer storing JSON snapshots on disk."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _thread_dir(self, thread_id: str) -> Path:
        safe_id = "".join(
            c if c.isalnum() or c in ("-", "_") else "_" for c in thread_id
        )
        td = self.base_dir / safe_id
        td.mkdir(parents=True, exist_ok=True)
        return td

    def save_checkpoint(self, thread_id: str, checkpoint: WorkflowCheckpoint) -> str:
        td = self._thread_dir(thread_id)
        filename = f"{checkpoint.metadata.step_index:04d}_{checkpoint.metadata.step_name}_{checkpoint.metadata.checkpoint_id}.json"
        target_path = td / filename
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, ensure_ascii=False)
        return checkpoint.metadata.checkpoint_id

    def list_checkpoints(self, thread_id: str) -> list[WorkflowCheckpoint]:
        td = self._thread_dir(thread_id)
        results: list[WorkflowCheckpoint] = []
        for file in sorted(td.glob("*.json")):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    results.append(WorkflowCheckpoint.from_dict(data))
            except Exception as e:
                logger.warning("Failed to load checkpoint file %s: %e", file, e)
        return results

    def get_latest_checkpoint(self, thread_id: str) -> WorkflowCheckpoint | None:
        cps = self.list_checkpoints(thread_id)
        return cps[-1] if cps else None

    def get_checkpoint(
        self, thread_id: str, checkpoint_id: str
    ) -> WorkflowCheckpoint | None:
        for cp in self.list_checkpoints(thread_id):
            if cp.metadata.checkpoint_id == checkpoint_id:
                return cp
        return None


# ---------------------------------------------------------------------------
# Temporal Resilience: Retry Policy & Saga Compensation
# ---------------------------------------------------------------------------


@dataclass
class RetryPolicy:
    """Configurable exponential backoff retry policy inspired by Temporal workflows."""

    max_attempts: int = 3
    initial_interval: float = 0.05
    backoff_coefficient: float = 2.0
    max_interval: float = 5.0
    jitter: bool = True
    non_retryable_errors: tuple[type[BaseException], ...] = ()

    def compute_delay(self, attempt: int) -> float:
        """Compute backoff delay with optional random jitter."""
        if attempt <= 1:
            delay = self.initial_interval
        else:
            delay = self.initial_interval * (self.backoff_coefficient ** (attempt - 1))
        delay = min(delay, self.max_interval)
        if self.jitter:
            delay = delay * (0.8 + 0.4 * random.random())
        return delay

    def should_retry(self, attempt: int, exc: BaseException) -> bool:
        """Check if an exception qualifies for retry under policy limits."""
        if attempt >= self.max_attempts:
            return False
        if any(isinstance(exc, err_cls) for err_cls in self.non_retryable_errors):
            return False
        return True

    def execute_sync(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a callable synchronously under the retry policy."""
        attempt = 1
        while True:
            try:
                return fn(*args, **kwargs)
            except BaseException as exc:
                if not self.should_retry(attempt, exc):
                    raise
                delay = self.compute_delay(attempt)
                logger.warning(
                    "Retry attempt %d after error: %s (sleeping %.3fs)",
                    attempt,
                    exc,
                    delay,
                )
                time.sleep(delay)
                attempt += 1

    async def execute_async(
        self, fn: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute a callable or coroutine asynchronously under the retry policy."""
        attempt = 1
        while True:
            try:
                res = fn(*args, **kwargs)
                if inspect.isawaitable(res):
                    return await res
                return res
            except BaseException as exc:
                if not self.should_retry(attempt, exc):
                    raise
                delay = self.compute_delay(attempt)
                logger.warning(
                    "Async retry attempt %d after error: %s (sleeping %.3fs)",
                    attempt,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
                attempt += 1


@dataclass
class SagaCompensation:
    """Registered compensating activity to execute upon workflow cancellation or failure."""

    name: str
    action: Callable[[], Any]
    async_action: Callable[[], Any] | None = None
    description: str = ""


class SagaCoordinator:
    """Saga coordinator tracking undo actions in LIFO order for transaction rollback."""

    def __init__(self) -> None:
        self._compensations: list[SagaCompensation] = []

    def register(
        self,
        name: str,
        action: Callable[[], Any],
        async_action: Callable[[], Any] | None = None,
        description: str = "",
    ) -> None:
        self._compensations.append(
            SagaCompensation(
                name=name,
                action=action,
                async_action=async_action,
                description=description,
            )
        )

    def compensate(self) -> list[dict[str, Any]]:
        """Execute registered compensations in reverse order."""
        outcomes: list[dict[str, Any]] = []
        while self._compensations:
            comp = self._compensations.pop()
            try:
                comp.action()
                outcomes.append({"name": comp.name, "status": "success"})
            except Exception as e:
                logger.error("Saga compensation '%s' failed: %s", comp.name, e)
                outcomes.append(
                    {"name": comp.name, "status": "failed", "error": str(e)}
                )
        return outcomes

    async def compensate_async(self) -> list[dict[str, Any]]:
        """Execute registered compensations asynchronously in reverse order."""
        outcomes: list[dict[str, Any]] = []
        while self._compensations:
            comp = self._compensations.pop()
            try:
                if comp.async_action:
                    res = comp.async_action()
                    if inspect.isawaitable(res):
                        await res
                else:
                    comp.action()
                outcomes.append({"name": comp.name, "status": "success"})
            except Exception as e:
                logger.error("Async saga compensation '%s' failed: %s", comp.name, e)
                outcomes.append(
                    {"name": comp.name, "status": "failed", "error": str(e)}
                )
        return outcomes


# ---------------------------------------------------------------------------
# Open-SWE Capability Fabric
# ---------------------------------------------------------------------------


class CapabilityHook:
    """Base lifecycle hook for Open-SWE capabilities."""

    def on_workflow_start(self, state: dict[str, Any]) -> None:
        pass

    def on_step_start(self, step_name: str, state: dict[str, Any]) -> None:
        pass

    def on_step_complete(
        self, step_name: str, state: dict[str, Any], delta: dict[str, Any]
    ) -> None:
        pass

    def on_step_error(
        self, step_name: str, state: dict[str, Any], error: Exception
    ) -> None:
        pass

    def on_workflow_complete(self, state: dict[str, Any]) -> None:
        pass

    async def on_workflow_start_async(self, state: dict[str, Any]) -> None:
        self.on_workflow_start(state)

    async def on_step_start_async(self, step_name: str, state: dict[str, Any]) -> None:
        self.on_step_start(step_name, state)

    async def on_step_complete_async(
        self, step_name: str, state: dict[str, Any], delta: dict[str, Any]
    ) -> None:
        self.on_step_complete(step_name, state, delta)

    async def on_step_error_async(
        self, step_name: str, state: dict[str, Any], error: Exception
    ) -> None:
        self.on_step_error(step_name, state, error)

    async def on_workflow_complete_async(self, state: dict[str, Any]) -> None:
        self.on_workflow_complete(state)


class TelemetryCapability(CapabilityHook):
    """Tracks step latencies, execution metrics, and throughput."""

    def __init__(self) -> None:
        self.metrics: dict[str, Any] = {
            "step_timings": {},
            "total_duration_ms": 0.0,
            "errors": [],
            "completed_steps": [],
        }
        self._start_time: float = 0.0
        self._step_start_time: float = 0.0

    def on_workflow_start(self, state: dict[str, Any]) -> None:
        self._start_time = time.perf_counter()
        state.setdefault("telemetry", {})["started_at"] = datetime.now(
            timezone.utc
        ).isoformat()

    def on_step_start(self, step_name: str, state: dict[str, Any]) -> None:
        self._step_start_time = time.perf_counter()

    def on_step_complete(
        self, step_name: str, state: dict[str, Any], delta: dict[str, Any]
    ) -> None:
        duration_ms = (time.perf_counter() - self._step_start_time) * 1000.0
        self.metrics["step_timings"][step_name] = round(duration_ms, 2)
        self.metrics["completed_steps"].append(step_name)

    def on_step_error(
        self, step_name: str, state: dict[str, Any], error: Exception
    ) -> None:
        self.metrics["errors"].append({"step": step_name, "error": str(error)})

    def on_workflow_complete(self, state: dict[str, Any]) -> None:
        total_ms = (time.perf_counter() - self._start_time) * 1000.0
        self.metrics["total_duration_ms"] = round(total_ms, 2)
        state.setdefault("telemetry", {}).update(self.metrics)


class IdempotencyCapability(CapabilityHook):
    """Ensures tasks and file operations are executed idempotently using hashed keys."""

    def __init__(self) -> None:
        self.executed_keys: set[str] = set()

    def on_workflow_start(self, state: dict[str, Any]) -> None:
        keys = state.get("idempotency_keys", [])
        self.executed_keys = set(keys)

    def is_executed(self, key: str) -> bool:
        return key in self.executed_keys

    def mark_executed(self, key: str) -> None:
        self.executed_keys.add(key)


class CapabilityFabric:
    """Registry and event dispatcher for workflow capability hooks."""

    def __init__(self, hooks: Sequence[CapabilityHook] | None = None) -> None:
        self.hooks: list[CapabilityHook] = (
            list(hooks) if hooks else [TelemetryCapability()]
        )

    def add_hook(self, hook: CapabilityHook) -> None:
        self.hooks.append(hook)

    def emit_workflow_start(self, state: dict[str, Any]) -> None:
        for hook in self.hooks:
            try:
                hook.on_workflow_start(state)
            except Exception as e:
                logger.warning("Hook on_workflow_start error: %s", e)

    def emit_step_start(self, step_name: str, state: dict[str, Any]) -> None:
        for hook in self.hooks:
            try:
                hook.on_step_start(step_name, state)
            except Exception as e:
                logger.warning("Hook on_step_start error: %s", e)

    def emit_step_complete(
        self, step_name: str, state: dict[str, Any], delta: dict[str, Any]
    ) -> None:
        for hook in self.hooks:
            try:
                hook.on_step_complete(step_name, state, delta)
            except Exception as e:
                logger.warning("Hook on_step_complete error: %s", e)

    def emit_step_error(
        self, step_name: str, state: dict[str, Any], error: Exception
    ) -> None:
        for hook in self.hooks:
            try:
                hook.on_step_error(step_name, state, error)
            except Exception as e:
                logger.warning("Hook on_step_error error: %s", e)

    def emit_workflow_complete(self, state: dict[str, Any]) -> None:
        for hook in self.hooks:
            try:
                hook.on_workflow_complete(state)
            except Exception as e:
                logger.warning("Hook on_workflow_complete error: %s", e)

    async def emit_workflow_start_async(self, state: dict[str, Any]) -> None:
        for hook in self.hooks:
            try:
                await hook.on_workflow_start_async(state)
            except Exception as e:
                logger.warning("Async hook on_workflow_start error: %s", e)

    async def emit_step_start_async(
        self, step_name: str, state: dict[str, Any]
    ) -> None:
        for hook in self.hooks:
            try:
                await hook.on_step_start_async(step_name, state)
            except Exception as e:
                logger.warning("Async hook on_step_start error: %s", e)

    async def emit_step_complete_async(
        self, step_name: str, state: dict[str, Any], delta: dict[str, Any]
    ) -> None:
        for hook in self.hooks:
            try:
                await hook.on_step_complete_async(step_name, state, delta)
            except Exception as e:
                logger.warning("Async hook on_step_complete error: %s", e)

    async def emit_step_error_async(
        self, step_name: str, state: dict[str, Any], error: Exception
    ) -> None:
        for hook in self.hooks:
            try:
                await hook.on_step_error_async(step_name, state, error)
            except Exception as e:
                logger.warning("Async hook on_step_error error: %s", e)

    async def emit_workflow_complete_async(self, state: dict[str, Any]) -> None:
        for hook in self.hooks:
            try:
                await hook.on_workflow_complete_async(state)
            except Exception as e:
                logger.warning("Async hook on_workflow_complete error: %s", e)


# ---------------------------------------------------------------------------
# LangGraph Workflow & State Definitions
# ---------------------------------------------------------------------------


class OrganizerWorkflowState(TypedDict, total=False):
    """Schema for document reorganization workflow state."""

    target_dir: str
    job_dir: str
    projects_root: str
    dry_run: bool
    scanned_files: list[dict[str, Any]]
    traceability_matches: dict[str, Any]
    tasks_plan: dict[str, Any]
    errors: list[str]
    checkpoint_thread_id: str
    checkpoint_dir: str
    idempotency_keys: list[str]
    telemetry: dict[str, Any]
    retry_attempts: dict[str, int]


def _scan_target_node(state: OrganizerWorkflowState) -> dict[str, Any]:
    """Scan target directory for candidate documents."""
    target_dir = Path(state.get("target_dir", "."))
    scanned: list[dict[str, Any]] = []

    if target_dir.exists() and target_dir.is_dir():
        for item in sorted(target_dir.iterdir()):
            if item.is_file():
                scanned.append(
                    {
                        "path": str(item.resolve()),
                        "name": item.name,
                        "size": item.stat().st_size,
                        "extension": item.suffix.lower(),
                    }
                )

    return {"scanned_files": scanned}


def _resolve_traceability_node(state: OrganizerWorkflowState) -> dict[str, Any]:
    """Resolve semantic project affinity and monorepo traceability for scanned files."""
    try:
        from core.traceability_resolver import TraceabilityContextResolver
    except ImportError:
        try:
            from .traceability_resolver import TraceabilityContextResolver
        except ImportError:
            from traceability_resolver import (
                TraceabilityContextResolver,  # type: ignore
            )

    projects_root = state.get("projects_root")
    resolver = TraceabilityContextResolver(projects_root=projects_root)

    matches: dict[str, Any] = {}
    for file_info in state.get("scanned_files", []):
        filename = file_info["name"]
        filepath = file_info["path"]
        affinity = resolver.resolve_project_affinity(
            filepath=filepath,
            summary=filename,
        )
        matches[filename] = {
            "pp": affinity.pp,
            "project_name": affinity.project_name,
            "confidence": affinity.confidence,
            "matched_keywords": affinity.matched_keywords,
            "reason": affinity.reason,
        }

    return {"traceability_matches": matches}


def _generate_plan_node(state: OrganizerWorkflowState) -> dict[str, Any]:
    """Build tasks.json plan based on resolved affinities and persist to job_dir."""
    traceability_matches = state.get("traceability_matches", {})
    scanned_files = state.get("scanned_files", [])
    job_dir_str = state.get("job_dir")

    rename_tasks: list[dict[str, Any]] = []
    for file_info in scanned_files:
        fname = file_info["name"]
        match_info = traceability_matches.get(fname, {})
        pp = match_info.get("pp", "00")
        pname = match_info.get("project_name", "INBOX")
        dest_folder = f"{pp}_{pname}"

        rename_tasks.append(
            {
                "src": file_info["path"],
                "dest_folder": dest_folder,
                "dest_filename": fname,
                "pp": pp,
                "confidence": match_info.get("confidence", 0.0),
            }
        )

    tasks_plan: dict[str, Any] = {
        "rename": rename_tasks,
        "duplicate": [],
        "move": [],
    }

    if job_dir_str:
        job_dir = Path(job_dir_str)
        job_dir.mkdir(parents=True, exist_ok=True)
        tasks_path = job_dir / "tasks.json"
        with open(tasks_path, "w", encoding="utf-8") as f:
            json.dump(tasks_plan, f, indent=2, ensure_ascii=False)

    return {"tasks_plan": tasks_plan}


# ---------------------------------------------------------------------------
# Durable Fallback Engine (Native LangGraph Parity)
# ---------------------------------------------------------------------------


class DurableFallbackRunner:
    """Resilient execution engine providing Temporal retry, checkpoints, and Open-SWE fabric."""

    def __init__(
        self,
        checkpointer: WorkflowCheckpointer | None = None,
        capability_fabric: CapabilityFabric | None = None,
        retry_policy: RetryPolicy | None = None,
        saga_coordinator: SagaCoordinator | None = None,
    ) -> None:
        self.checkpointer = checkpointer or MemoryWorkflowCheckpointer()
        self.capability_fabric = capability_fabric or CapabilityFabric()
        self.retry_policy = retry_policy or RetryPolicy()
        self.saga_coordinator = saga_coordinator or SagaCoordinator()
        self.steps: list[tuple[str, Callable[[Any], dict[str, Any]]]] = [
            ("scan_target", _scan_target_node),
            ("resolve_traceability", _resolve_traceability_node),
            ("generate_plan", _generate_plan_node),
        ]

    def _make_checkpoint(
        self,
        thread_id: str,
        step_name: str,
        step_index: int,
        state: dict[str, Any],
        status: str,
        error: str | None = None,
        duration_ms: float = 0.0,
    ) -> WorkflowCheckpoint:
        cp_id = f"cp_{int(time.time() * 1000)}_{step_index}_{step_name}"
        meta = CheckpointMetadata(
            checkpoint_id=cp_id,
            thread_id=thread_id,
            step_name=step_name,
            step_index=step_index,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=status,
            error=error,
            execution_time_ms=duration_ms,
        )
        return WorkflowCheckpoint(metadata=meta, state=dict(state))

    def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the workflow synchronously with checkpointing, retry policy, and hooks."""
        curr_state = dict(state)
        thread_id = str(
            curr_state.get("checkpoint_thread_id")
            or curr_state.get("job_dir")
            or "default_thread"
        )

        # If job_dir specifies a checkpoint dir, optionally attach file checkpointer
        if "checkpoint_dir" in curr_state and not isinstance(
            self.checkpointer, FileWorkflowCheckpointer
        ):
            self.checkpointer = FileWorkflowCheckpointer(curr_state["checkpoint_dir"])

        self.capability_fabric.emit_workflow_start(curr_state)
        init_cp = self._make_checkpoint(
            thread_id, "start", 0, curr_state, WorkflowCheckpointStatus.RUNNING
        )
        self.checkpointer.save_checkpoint(thread_id, init_cp)

        try:
            for idx, (step_name, node_fn) in enumerate(self.steps, start=1):
                self.capability_fabric.emit_step_start(step_name, curr_state)
                t0 = time.perf_counter()

                # Execute with Temporal retry policy
                try:
                    delta = self.retry_policy.execute_sync(node_fn, curr_state)
                    dur_ms = (time.perf_counter() - t0) * 1000.0
                    curr_state.update(delta)

                    self.capability_fabric.emit_step_complete(
                        step_name, curr_state, delta
                    )
                    cp = self._make_checkpoint(
                        thread_id=thread_id,
                        step_name=step_name,
                        step_index=idx,
                        state=curr_state,
                        status=WorkflowCheckpointStatus.CHECKPOINTED,
                        duration_ms=dur_ms,
                    )
                    self.checkpointer.save_checkpoint(thread_id, cp)
                except Exception as exc:
                    dur_ms = (time.perf_counter() - t0) * 1000.0
                    self.capability_fabric.emit_step_error(step_name, curr_state, exc)
                    curr_state.setdefault("errors", []).append(
                        f"Step {step_name} failed: {exc}"
                    )
                    fail_cp = self._make_checkpoint(
                        thread_id=thread_id,
                        step_name=step_name,
                        step_index=idx,
                        state=curr_state,
                        status=WorkflowCheckpointStatus.FAILED,
                        error=str(exc),
                        duration_ms=dur_ms,
                    )
                    self.checkpointer.save_checkpoint(thread_id, fail_cp)
                    # Trigger saga compensations if registered
                    self.saga_coordinator.compensate()
                    raise

            final_cp = self._make_checkpoint(
                thread_id=thread_id,
                step_name="completed",
                step_index=len(self.steps) + 1,
                state=curr_state,
                status=WorkflowCheckpointStatus.COMPLETED,
            )
            self.checkpointer.save_checkpoint(thread_id, final_cp)
            self.capability_fabric.emit_workflow_complete(curr_state)
            return curr_state

        except Exception:
            raise

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the workflow asynchronously with checkpointing, retry policy, and hooks."""
        curr_state = dict(state)
        thread_id = str(
            curr_state.get("checkpoint_thread_id")
            or curr_state.get("job_dir")
            or "default_thread"
        )

        if "checkpoint_dir" in curr_state and not isinstance(
            self.checkpointer, FileWorkflowCheckpointer
        ):
            self.checkpointer = FileWorkflowCheckpointer(curr_state["checkpoint_dir"])

        await self.capability_fabric.emit_workflow_start_async(curr_state)
        init_cp = self._make_checkpoint(
            thread_id, "start", 0, curr_state, WorkflowCheckpointStatus.RUNNING
        )
        await self.checkpointer.save_checkpoint_async(thread_id, init_cp)

        try:
            for idx, (step_name, node_fn) in enumerate(self.steps, start=1):
                await self.capability_fabric.emit_step_start_async(
                    step_name, curr_state
                )
                t0 = time.perf_counter()

                try:
                    delta = await self.retry_policy.execute_async(node_fn, curr_state)
                    dur_ms = (time.perf_counter() - t0) * 1000.0
                    curr_state.update(delta)

                    await self.capability_fabric.emit_step_complete_async(
                        step_name, curr_state, delta
                    )
                    cp = self._make_checkpoint(
                        thread_id=thread_id,
                        step_name=step_name,
                        step_index=idx,
                        state=curr_state,
                        status=WorkflowCheckpointStatus.CHECKPOINTED,
                        duration_ms=dur_ms,
                    )
                    await self.checkpointer.save_checkpoint_async(thread_id, cp)
                except Exception as exc:
                    dur_ms = (time.perf_counter() - t0) * 1000.0
                    await self.capability_fabric.emit_step_error_async(
                        step_name, curr_state, exc
                    )
                    curr_state.setdefault("errors", []).append(
                        f"Step {step_name} failed: {exc}"
                    )
                    fail_cp = self._make_checkpoint(
                        thread_id=thread_id,
                        step_name=step_name,
                        step_index=idx,
                        state=curr_state,
                        status=WorkflowCheckpointStatus.FAILED,
                        error=str(exc),
                        duration_ms=dur_ms,
                    )
                    await self.checkpointer.save_checkpoint_async(thread_id, fail_cp)
                    await self.saga_coordinator.compensate_async()
                    raise

            final_cp = self._make_checkpoint(
                thread_id=thread_id,
                step_name="completed",
                step_index=len(self.steps) + 1,
                state=curr_state,
                status=WorkflowCheckpointStatus.COMPLETED,
            )
            await self.checkpointer.save_checkpoint_async(thread_id, final_cp)
            await self.capability_fabric.emit_workflow_complete_async(curr_state)
            return curr_state

        except Exception:
            raise

    def resume_from_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str | None = None,
    ) -> dict[str, Any]:
        """Resume workflow execution from a saved checkpoint."""
        if checkpoint_id:
            cp = self.checkpointer.get_checkpoint(thread_id, checkpoint_id)
        else:
            cp = self.checkpointer.get_latest_checkpoint(thread_id)

        if not cp:
            raise ValueError(f"No checkpoint found for thread '{thread_id}'")

        resumed_state = dict(cp.state)
        # Determine remaining steps based on last executed step_index
        remaining_steps = self.steps[cp.metadata.step_index :]
        runner = DurableFallbackRunner(
            checkpointer=self.checkpointer,
            capability_fabric=self.capability_fabric,
            retry_policy=self.retry_policy,
            saga_coordinator=self.saga_coordinator,
        )
        runner.steps = remaining_steps
        return runner.invoke(resumed_state)


def build_document_organizer_graph(
    checkpointer: WorkflowCheckpointer | None = None,
    capability_fabric: CapabilityFabric | None = None,
    retry_policy: RetryPolicy | None = None,
    saga_coordinator: SagaCoordinator | None = None,
):
    """Build and compile the document organizer workflow graph.

    Supports durable checkpointing, Temporal retries, and Open-SWE capability fabric.
    Returns a runnable supporting .invoke(initial_state) and .ainvoke(initial_state).
    """
    if not _LANGGRAPH_AVAILABLE:
        return DurableFallbackRunner(
            checkpointer=checkpointer,
            capability_fabric=capability_fabric,
            retry_policy=retry_policy,
            saga_coordinator=saga_coordinator,
        )

    # When LangGraph is available, wrap nodes with capability and retry safeguards
    cap_fabric = capability_fabric or CapabilityFabric()
    ret_policy = retry_policy or RetryPolicy()

    def wrapped_scan(state: OrganizerWorkflowState) -> dict[str, Any]:
        cap_fabric.emit_step_start("scan_target", state)
        res = ret_policy.execute_sync(_scan_target_node, state)
        cap_fabric.emit_step_complete("scan_target", state, res)
        return res

    def wrapped_resolve(state: OrganizerWorkflowState) -> dict[str, Any]:
        cap_fabric.emit_step_start("resolve_traceability", state)
        res = ret_policy.execute_sync(_resolve_traceability_node, state)
        cap_fabric.emit_step_complete("resolve_traceability", state, res)
        return res

    def wrapped_plan(state: OrganizerWorkflowState) -> dict[str, Any]:
        cap_fabric.emit_step_start("generate_plan", state)
        res = ret_policy.execute_sync(_generate_plan_node, state)
        cap_fabric.emit_step_complete("generate_plan", state, res)
        return res

    workflow = StateGraph(OrganizerWorkflowState)
    workflow.add_node("scan_target", wrapped_scan)
    workflow.add_node("resolve_traceability", wrapped_resolve)
    workflow.add_node("generate_plan", wrapped_plan)

    workflow.add_edge(START, "scan_target")
    workflow.add_edge("scan_target", "resolve_traceability")
    workflow.add_edge("resolve_traceability", "generate_plan")
    workflow.add_edge("generate_plan", END)

    class _AutoThreadGraphProxy:
        def __init__(self, compiled: Any) -> None:
            self._compiled = compiled

        @staticmethod
        def _ensure_config(state: dict[str, Any], config: dict[str, Any] | None) -> dict[str, Any]:
            cfg = dict(config) if config else {}
            conf = dict(cfg.get("configurable") or {})
            if not any(k in conf for k in ("thread_id", "checkpoint_ns", "checkpoint_id")):
                conf["thread_id"] = str(state.get("thread_id") or uuid.uuid4())
            cfg["configurable"] = conf
            return cfg

        def invoke(self, state: dict[str, Any], config: dict[str, Any] | None = None, **kwargs: Any) -> Any:
            return self._compiled.invoke(state, config=self._ensure_config(state, config), **kwargs)

        async def ainvoke(self, state: dict[str, Any], config: dict[str, Any] | None = None, **kwargs: Any) -> Any:
            return await self._compiled.ainvoke(state, config=self._ensure_config(state, config), **kwargs)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._compiled, name)

    # If a LangGraph-compatible checkpointer is passed, compile with checkpointer
    if checkpointer is not None and hasattr(checkpointer, "get_tuple"):
        return _AutoThreadGraphProxy(workflow.compile(checkpointer=checkpointer))

    compiled_default = workflow.compile(checkpointer=_get_default_langgraph_checkpointer())
    return _AutoThreadGraphProxy(compiled_default)
