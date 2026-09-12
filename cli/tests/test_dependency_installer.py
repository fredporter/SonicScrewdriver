"""Unit tests for Sonic offline dependency installer, integrity verification, and safe uninstaller."""

from pathlib import Path
import zipfile
import pytest

from sonic.lib.dependency_installer import (
    DependencyConflictError,
    PackageIntegrityError,
    PackageSecurityError,
    build_package,
    install_package,
    is_protected_user_path,
    list_installed_packages,
    uninstall_package,
    verify_package,
)


@pytest.fixture
def dummy_source_dir(tmp_path: Path) -> Path:
    src = tmp_path / "source_lib"
    src.mkdir()
    (src / "lib.py").write_text("def hello(): return 'world'\n", encoding="utf-8")
    (src / "config.json").write_text('{"active": true}\n', encoding="utf-8")
    return src


def test_build_and_install_package(dummy_source_dir: Path, tmp_path: Path):
    pkg_file = tmp_path / "test-pkg.spkg"
    build_package(
        source_dir=dummy_source_dir,
        output_file=pkg_file,
        name="test-lib",
        version="1.0.0",
        description="A test library package",
    )

    assert pkg_file.exists()

    install_root = tmp_path / "packages_store"
    res = install_package(pkg_file, consumer_id="uCode", packages_root=install_root)

    assert res["status"] == "installed"
    assert res["name"] == "test-lib"
    assert res["version"] == "1.0.0"
    assert "uCode" in res["required_by"]

    installed_file = install_root / "test-lib" / "1.0.0" / "lib.py"
    assert installed_file.exists()
    assert "def hello" in installed_file.read_text(encoding="utf-8")


def test_reuse_installed_package_and_add_consumer(dummy_source_dir: Path, tmp_path: Path):
    pkg_file = tmp_path / "test-pkg.spkg"
    build_package(dummy_source_dir, pkg_file, name="test-lib", version="1.0.0")

    install_root = tmp_path / "packages_store"
    res1 = install_package(pkg_file, consumer_id="uCode", packages_root=install_root)
    assert res1["status"] == "installed"

    # Install same package for a different consumer
    res2 = install_package(pkg_file, consumer_id="HomeNest", packages_root=install_root)
    assert res2["status"] == "reused"
    assert set(res2["required_by"]) == {"uCode", "HomeNest"}


def test_version_conflict_rejection(dummy_source_dir: Path, tmp_path: Path):
    pkg_v1 = tmp_path / "test-pkg-1.0.0.spkg"
    build_package(dummy_source_dir, pkg_v1, name="test-lib", version="1.0.0")

    pkg_v2 = tmp_path / "test-pkg-2.0.0.spkg"
    build_package(dummy_source_dir, pkg_v2, name="test-lib", version="2.0.0")

    install_root = tmp_path / "packages_store"
    install_package(pkg_v1, consumer_id="uCode", packages_root=install_root)

    # Attempting to install v2.0.0 over existing v1.0.0 must raise DependencyConflictError
    with pytest.raises(DependencyConflictError) as exc_info:
        install_package(pkg_v2, consumer_id="OtherApp", packages_root=install_root)
    assert "Version conflict for package 'test-lib'" in str(exc_info.value)


def test_integrity_verification_failure(dummy_source_dir: Path, tmp_path: Path):
    pkg_file = tmp_path / "test-pkg.spkg"
    build_package(dummy_source_dir, pkg_file, name="test-lib", version="1.0.0")

    # Corrupt payload inside archive
    tampered_pkg = tmp_path / "tampered.spkg"
    with zipfile.ZipFile(pkg_file, "r") as src_z:
        with zipfile.ZipFile(tampered_pkg, "w") as dst_z:
            for item in src_z.infolist():
                if item.filename == "payload/lib.py":
                    dst_z.writestr(item, b"MALICIOUS_PAYLOAD")
                else:
                    dst_z.writestr(item, src_z.read(item.filename))

    install_root = tmp_path / "packages_store"
    with pytest.raises(PackageIntegrityError) as exc_info:
        install_package(tampered_pkg, consumer_id="uCode", packages_root=install_root)
    assert "SHA-256 integrity check failed" in str(exc_info.value)


def test_shared_dependency_retention_and_safe_uninstall(dummy_source_dir: Path, tmp_path: Path):
    pkg_file = tmp_path / "test-pkg.spkg"
    build_package(dummy_source_dir, pkg_file, name="test-lib", version="1.0.0")

    install_root = tmp_path / "packages_store"
    install_package(pkg_file, consumer_id="uCode", packages_root=install_root)
    install_package(pkg_file, consumer_id="HomeNest", packages_root=install_root)

    # Uninstall by uCode: should be retained because HomeNest still requires it
    un1 = uninstall_package("test-lib", consumer_id="uCode", packages_root=install_root)
    assert un1["status"] == "retained"
    assert "HomeNest" in un1["remaining_consumers"]
    assert (install_root / "test-lib" / "1.0.0" / "lib.py").exists()

    # Uninstall by HomeNest (last consumer): should delete package files
    un2 = uninstall_package("test-lib", consumer_id="HomeNest", packages_root=install_root)
    assert un2["status"] == "uninstalled"
    assert not (install_root / "test-lib").exists()


def test_user_document_protection():
    home = Path.home()
    assert is_protected_user_path(home / "Vault" / "secret.md")
    assert is_protected_user_path(home / "Shared" / "data.csv")
    assert is_protected_user_path(home / "Public" / "doc.txt")
    assert is_protected_user_path(home / ".ssh" / "id_rsa")
    assert not is_protected_user_path(home / "Code" / ".udos" / "packages")
