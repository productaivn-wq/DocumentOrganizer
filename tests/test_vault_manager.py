import json
import tempfile
from pathlib import Path

from DocumentOrganizer.scripts.vault_manager import (
    VaultManager,
    calculate_sha256,
    normalize_alias,
)


def test_vault_init_and_scaffolding():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault"
        vm = VaultManager(vault_path)
        res = vm.init_vault("Test Owner")

        assert res["success"] is True
        assert (vault_path / "01_identity_personal").exists()
        assert (vault_path / "02_business_registrations").exists()
        assert (vault_path / "03_premises_and_contracts").exists()
        assert (vault_path / "04_banking_and_finance").exists()
        assert (vault_path / "05_dispatch_registry").exists()
        assert (vault_path / "manifest.json").exists()
        assert (vault_path / "README.md").exists()
        assert (vault_path / "vault_resolver.py").exists()


def test_vault_asset_registration_and_resolution():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault"
        vm = VaultManager(vault_path)
        vm.init_vault("Test Owner")

        # Create dummy document in 01_identity_personal
        doc_file = vault_path / "01_identity_personal" / "test_passport.pdf"
        doc_file.write_text("DUMMY_PASSPORT_CONTENT_FOR_HASHING")

        reg_res = vm.register_assets()
        assert reg_res["success"] is True
        assert reg_res["total_assets"] >= 1

        # Check manifest
        with open(vm.manifest_file, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        expected_alias = normalize_alias("01_identity_personal", doc_file)
        assert expected_alias in manifest["assets"]
        asset_meta = manifest["assets"][expected_alias]
        assert asset_meta["filename"] == "test_passport.pdf"
        assert asset_meta["sha256"] == calculate_sha256(doc_file)

        # Test resolution
        resolved_path = vm.resolve(expected_alias)
        assert resolved_path == doc_file


def test_vault_dispatch_export():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir) / "test_vault"
        export_path = Path(tmpdir) / "export_dest"
        vm = VaultManager(vault_path)
        vm.init_vault("Test Owner")

        doc_file = vault_path / "03_premises_and_contracts" / "lease_contract.pdf"
        doc_file.write_text("SAMPLE_CONTRACT_BYTES")
        vm.register_assets()

        alias = normalize_alias("03_premises_and_contracts", doc_file)
        disp_res = vm.dispatch(alias, channel="export", target_id=str(export_path))

        assert disp_res["success"] is True
        assert (export_path / "lease_contract.pdf").exists()
        assert (vault_path / "05_dispatch_registry" / "dispatch_log.jsonl").exists()
