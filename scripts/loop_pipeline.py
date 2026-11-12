"""Looping daemon pipeline for automated document ingestion and organization."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from .consolidate_workspace import run_workspace_consolidation
from .logger import setup_logger

logger = setup_logger("DocumentOrganizer.LoopPipeline")


class LoopPipeline:
    """Headless loop pipeline for continuous workspace organization."""

    def __init__(
        self,
        workspace_dir: Path,
        target_dir: Path,
        interval_seconds: int = 60,
        max_iterations: int = 0,
    ) -> None:
        self.workspace_dir = workspace_dir
        self.target_dir = target_dir
        self.interval_seconds = interval_seconds
        self.max_iterations = max_iterations

    def execute_cycle(self) -> None:
        """Run single cycle of extraction, consolidation, and cleanup."""
        logger.info("Starting pipeline cycle...")
        run_workspace_consolidation(self.workspace_dir, self.target_dir, dry_run=False)
        logger.info("Pipeline cycle completed.")

    def run(self) -> None:
        """Continuous execution loop."""
        iteration = 0
        logger.info(
            "Running loop pipeline on %s -> %s (interval: %ds)",
            self.workspace_dir,
            self.target_dir,
            self.interval_seconds,
        )
        try:
            while True:
                iteration += 1
                self.execute_cycle()
                if self.max_iterations > 0 and iteration >= self.max_iterations:
                    logger.info(
                        "Reached maximum iterations (%d). Stopping.",
                        self.max_iterations,
                    )
                    break
                time.sleep(self.interval_seconds)
        except KeyboardInterrupt:
            logger.info("Pipeline terminated by user interrupt.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Continuous Document Pipeline")
    parser.add_argument(
        "--workspace", required=True, type=Path, help="Source workspace"
    )
    parser.add_argument("--target", required=True, type=Path, help="Destination folder")
    parser.add_argument(
        "--interval", type=int, default=60, help="Loop interval in seconds"
    )
    parser.add_argument(
        "--max-iterations", type=int, default=0, help="Max iterations (0 for infinite)"
    )
    args = parser.parse_args()

    pipeline = LoopPipeline(
        workspace_dir=args.workspace,
        target_dir=args.target,
        interval_seconds=args.interval,
        max_iterations=args.max_iterations,
    )
    pipeline.run()


if __name__ == "__main__":
    main()
