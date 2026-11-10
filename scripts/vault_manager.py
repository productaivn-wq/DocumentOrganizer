"""
vault_manager.py — Personal & Enterprise Legal Vault Manager with Zero-LLM Dispatch.
Part of DocumentOrganizer v2.2.0.

Provides:
1. Deterministic Vault Scaffolding (MECE 01-05 zones).
2. Semantic Versioning & Automated SHA-256 Manifest Registration.
3. Zero-LLM Data Plane Resolution & Local Wire Dispatch.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import mimetypes
import os
import shutil
import sys
from pathlib import Path
from typing import Any

VAULT_ZONES = [
    (
        "01_identity_personal",
        "National ID, passports, driver licenses, and personal profile metadata.",
    ),
    (
        "02_business_registrations",
        "Business registration certificates, amendments, and official filings sorted by semantic version.",
    ),
    (
        "03_premises_and_contracts",
        "Lease agreements, office location documents, property rights, and commercial contracts.",
    ),
    (
        "04_banking_and_finance",
        "Bank accounts, merchant accounts, payment standees, and financial liaison contacts.",
    ),
    (
        "05_dispatch_registry",
        "Transmission audit logs, recipient acknowledgments, and delivery receipts.",
    ),
]


def calculate_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file efficiently in 64KB chunks."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def normalize_alias(zone_name: str, file_path: Path) -> str:
    """Generate a clean, deterministic uppercase alias like DOC_IDENTITY_PASSPORT."""
    zone_prefix = zone_name.split("_", 1)[-1].upper()
    stem = file_path.stem.upper()
    # Clean unwanted symbols
    clean_stem = "".join(c if c.isalnum() else "_" for c in stem)
    clean_stem = "_".join(filter(None, clean_stem.split("_")))
    return f"DOC_{zone_prefix}_{clean_stem}"


class VaultManager:
    """Core controller for Personal & Business Legal Vaults."""

    def __init__(self, vault_root: Path) -> None:
        self.vault_root = Path(vault_root).resolve()
        self.manifest_file = self.vault_root / "manifest.json"
        self.readme_file = self.vault_root / "README.md"
        self.dispatch_log = (
            self.vault_root / "05_dispatch_registry" / "dispatch_log.jsonl"
        )

    def init_vault(self, owner_name: str = "Authorized Owner") -> dict[str, Any]:
        """Scaffold standard MECE vault structure and initial manifests."""
        self.vault_root.mkdir(parents=True, exist_ok=True)
        created_zones = []

        for zone_dir, desc in VAULT_ZONES:
            zd = self.vault_root / zone_dir
            zd.mkdir(parents=True, exist_ok=True)
            created_zones.append(zone_dir)

        # Standard sub-versions for business registrations
        dkkd_dir = self.vault_root / "02_business_registrations"
        (dkkd_dir / "v1.0_initial_establishment").mkdir(exist_ok=True)
        (dkkd_dir / "v2.0_amendment_filing").mkdir(exist_ok=True)
        (dkkd_dir / "v2.1_amendment_supplementary").mkdir(exist_ok=True)
        (dkkd_dir / "v3.0_official_certificate_issued").mkdir(exist_ok=True)

        manifest_data = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "vault_version": "1.0.0",
            "owner": owner_name,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "root": str(self.vault_root),
            "assets": {},
        }
        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)

        self._write_resolver_script()
        self.register_assets()

        return {
            "success": True,
            "vault_root": str(self.vault_root),
            "zones": created_zones,
        }

    def _write_resolver_script(self) -> None:
        """Deploy deterministic Zero-LLM resolver script inside the vault."""
        resolver_path = self.vault_root / "vault_resolver.py"
        content = """# Deterministic Zero-LLM Asset Resolver
import sys, json
from pathlib import Path

MANIFEST = Path(__file__).resolve().parent / "manifest.json"

def resolve(alias: str) -> str:
    with open(MANIFEST, "r", encoding="utf-8") as f:
        data = json.load(f)
    assets = data.get("assets", {})
    if alias not in assets:
        raise KeyError(f"Asset '{alias}' not found in manifest.")
    return assets[alias]["absolute_path"]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            print(resolve(sys.argv[1]))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
"""
        with open(resolver_path, "w", encoding="utf-8") as f:
            f.write(content)

    def register_assets(self) -> dict[str, Any]:
        """Scan all files across vault, compute hashes, update manifest.json and README.md."""
        if not self.vault_root.exists():
            raise FileNotFoundError(
                f"Vault directory does not exist: {self.vault_root}"
            )

        existing_manifest: dict[str, Any] = {}
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    existing_manifest = json.load(f)
            except Exception:
                existing_manifest = {}

        existing_assets = existing_manifest.get("assets", {})
        registered_assets: dict[str, Any] = {}

        # Traversal ignoring hidden files, system files, scripts, and logs
        ignore_files = {"manifest.json", "README.md", "vault_resolver.py"}

        for zone_dir, desc in VAULT_ZONES:
            zone_path = self.vault_root / zone_dir
            if not zone_path.exists():
                continue

            for root, dirs, files in os.walk(zone_path):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for f in files:
                    if f in ignore_files or f.endswith(".jsonl") or f.endswith(".py"):
                        continue

                    full_path = Path(root) / f
                    rel_path = full_path.relative_to(self.vault_root)

                    # Determine alias: check if already assigned in existing manifest
                    matched_alias = None
                    for al, meta in existing_assets.items():
                        if meta.get("relative_path") == str(rel_path).replace(
                            "\\", "/"
                        ):
                            matched_alias = al
                            break

                    if not matched_alias:
                        matched_alias = normalize_alias(zone_dir, full_path)

                    file_stat = full_path.stat()
                    mime, _ = mimetypes.guess_type(str(full_path))
                    sha256 = calculate_sha256(full_path)

                    # Retain user metadata if present
                    old_meta = existing_assets.get(matched_alias, {})
                    status = old_meta.get("status", "ACTIVE_VERIFIED")
                    if (
                        "superseded" in str(rel_path).lower()
                        or "legacy" in str(rel_path).lower()
                    ):
                        status = "SUPERSEDED"

                    registered_assets[matched_alias] = {
                        "alias": matched_alias,
                        "filename": full_path.name,
                        "relative_path": str(rel_path).replace("\\", "/"),
                        "absolute_path": str(full_path),
                        "size_bytes": file_stat.st_size,
                        "sha256": sha256,
                        "version": old_meta.get("version", "1.0"),
                        "classification": old_meta.get(
                            "classification", "CONFIDENTIAL"
                        ),
                        "status": status,
                        "mime_type": mime or "application/octet-stream",
                        "description": old_meta.get(
                            "description", f"Document in {zone_dir}"
                        ),
                        "updated_at": datetime.datetime.fromtimestamp(
                            file_stat.st_mtime
                        ).isoformat(),
                    }

        updated_manifest = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "vault_version": existing_manifest.get("vault_version", "1.0.0"),
            "owner": existing_manifest.get("owner", "Authorized Owner"),
            "updated_at": datetime.datetime.now().isoformat(),
            "root": str(self.vault_root),
            "assets": registered_assets,
        }

        with open(self.manifest_file, "w", encoding="utf-8") as f:
            json.dump(updated_manifest, f, ensure_ascii=False, indent=2)

        self._generate_readme(updated_manifest)

        return {
            "success": True,
            "total_assets": len(registered_assets),
            "manifest_file": str(self.manifest_file),
        }

    def _generate_readme(self, manifest: dict[str, Any]) -> None:
        """Generate human-readable SSOT Catalog markdown with file:// links."""
        lines = [
            "# Personal & Business Legal Vault",
            "",
            f"- **Vault Root**: `{self.vault_root}`",
            f"- **Owner**: {manifest.get('owner', 'Authorized Owner')}",
            f"- **Last Updated**: {manifest.get('updated_at', '')}",
            "- **Standard**: DocumentOrganizer v2.2.0 · Zero-LLM Data Plane",
            "",
            "---",
            "",
            "## 1. Zero-LLM File Reference Architecture",
            "",
            "This vault adheres to the **Zero-LLM Ingestion Invariant**: raw binary/PDF documents are",
            "**NEVER piped through LLM prompts, context tokens, or external API payloads**.",
            "Instead, the LLM reasons solely on opaque *Aliases* (`DOC_*`). Local deterministic software",
            "resolves the local file path on disk and transmits bytes directly over localhost/TLS.",
            "",
            "---",
            "",
            "## 2. Master Registered Assets (SSOT Registry)",
            "",
            "| Alias | File Name | Version | Status | Size | SHA-256 (Truncated) | Local Link |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :--- |",
        ]

        assets = manifest.get("assets", {})
        for alias, meta in sorted(assets.items(), key=lambda x: x[0]):
            fn = meta.get("filename", "")
            ver = meta.get("version", "1.0")
            st = meta.get("status", "ACTIVE")
            sz = f"{round(meta.get('size_bytes', 0) / 1024, 1)} KB"
            sha = meta.get("sha256", "")[:12] + "..."
            abs_p = meta.get("absolute_path", "").replace("\\", "/")
            lines.append(
                f"| `{alias}` | `{fn}` | {ver} | `{st}` | {sz} | `{sha}` | [Mở File](file:///{abs_p}) |"
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 3. Usage Reference (Local Dispatch)",
                "",
                "```bash",
                "# List all registered assets",
                f'python -m DocumentOrganizer.scripts.vault_manager list --vault "{self.vault_root}"',
                "",
                "# Resolve file path by alias (Zero LLM overhead)",
                f'python -m DocumentOrganizer.scripts.vault_manager resolve --vault "{self.vault_root}" --alias DOC_IDENTITY_PASSPORT',
                "```",
            ]
        )

        with open(self.readme_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def resolve(self, alias: str) -> Path:
        """Resolve alias to absolute file path without inspecting file contents."""
        if not self.manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found at {self.manifest_file}")

        with open(self.manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assets = data.get("assets", {})
        if alias not in assets:
            raise KeyError(
                f"Asset '{alias}' is not registered. Available: {list(assets.keys())}"
            )

        target_path = Path(assets[alias]["absolute_path"])
        if not target_path.exists():
            raise FileNotFoundError(
                f"Registered file is missing on disk: {target_path}"
            )

        return target_path

    def dispatch(
        self,
        alias: str,
        channel: str,
        target_id: str,
        message: str = "",
        thread_type: int = 0,
    ) -> dict[str, Any]:
        """
        Dispatch registered asset directly from local disk to local export destination.
        Zero file content enters LLM context.
        """
        file_path = self.resolve(alias)

        dispatch_record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "alias": alias,
            "filename": file_path.name,
            "channel": channel,
            "target_id": target_id,
            "status": "pending",
        }

        result = {}
        if channel.lower() == "export":
            dest_dir = Path(target_id)
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest_dir / file_path.name)
            dispatch_record["status"] = "success"
            result = {"success": True, "exported_to": str(dest_dir / file_path.name)}
        else:
            raise ValueError(
                f"Unsupported channel '{channel}'. Supported: 'export'."
            )

        # Append to audit log
        self.dispatch_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.dispatch_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(dispatch_record, ensure_ascii=False) + "\n")

        return {
            "success": True,
            "alias": alias,
            "file_dispatched": str(file_path),
            "record": dispatch_record,
            "result": result,
        }


def main():
    parser = argparse.ArgumentParser(
        description="DocumentOrganizer Vault Manager & Zero-LLM Dispatcher"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Init
    p_init = subparsers.add_parser("init", help="Initialize a new legal vault")
    p_init.add_argument("--vault", required=True, help="Path to vault root")
    p_init.add_argument("--owner", default="Authorized Owner", help="Owner name")

    # Register
    p_reg = subparsers.add_parser("register", help="Register/index all files in vault")
    p_reg.add_argument("--vault", required=True, help="Path to vault root")

    # List
    p_list = subparsers.add_parser("list", help="List registered assets")
    p_list.add_argument("--vault", required=True, help="Path to vault root")

    # Resolve
    p_res = subparsers.add_parser("resolve", help="Resolve asset alias to local path")
    p_res.add_argument("--vault", required=True, help="Path to vault root")
    p_res.add_argument("--alias", required=True, help="Asset alias")

    # Dispatch
    p_disp = subparsers.add_parser(
        "dispatch", help="Directly dispatch asset without LLM context"
    )
    p_disp.add_argument("--vault", required=True, help="Path to vault root")
    p_disp.add_argument("--alias", required=True, help="Asset alias")
    p_disp.add_argument(
        "--channel", default="zalo", help="Target channel (zalo, export)"
    )
    p_disp.add_argument(
        "--target", required=True, help="Target recipient ID or export path"
    )
    p_disp.add_argument("--message", default="", help="Optional caption/message")

    args = parser.parse_args()
    vm = VaultManager(Path(args.vault))

    if args.command == "init":
        res = vm.init_vault(args.owner)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.command == "register":
        res = vm.register_assets()
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.command == "list":
        if not vm.manifest_file.exists():
            print("Vault manifest not found. Run register first.")
            sys.exit(1)
        with open(vm.manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for a, m in data.get("assets", {}).items():
            print(
                f"{a:<32} | {m.get('version', '1.0'):<5} | {m.get('status', ''):<24} | {m.get('filename')}"
            )
    elif args.command == "resolve":
        path = vm.resolve(args.alias)
        print(str(path))
    elif args.command == "dispatch":
        res = vm.dispatch(args.alias, args.channel, args.target, args.message)
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
