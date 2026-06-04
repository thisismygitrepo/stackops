import importlib.util
import sys
from pathlib import Path


def _load_pwdmgr_module():
    module_path = Path(__file__).resolve().parents[1] / "pwdmgr.py"
    spec = importlib.util.spec_from_file_location("pwdmgr_under_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pwdmgr_under_test"] = module
    spec.loader.exec_module(module)
    return module


pwdmgr = _load_pwdmgr_module()


def test_pwdmgr_cache_uses_stackops_gpg_helpers(monkeypatch, tmp_path: Path) -> None:
    cache_path = tmp_path / "tmp_results" / "cache" / "pwdmgr" / "cache.json.gpg"
    calls: list[tuple[str, bytes]] = []

    monkeypatch.setattr(pwdmgr, "CACHE_PATH", cache_path)

    def fake_encrypt(data: bytes) -> bytes:
        calls.append(("encrypt", data))
        return b"gpg:" + data

    def fake_decrypt(data: bytes) -> bytes:
        calls.append(("decrypt", data))
        assert data.startswith(b"gpg:")
        return data.removeprefix(b"gpg:")

    monkeypatch.setattr(pwdmgr, "encrypt_bytes_asymmetric", fake_encrypt)
    monkeypatch.setattr(pwdmgr, "decrypt_bytes_asymmetric", fake_decrypt)

    pwdmgr.save_encrypted_cache({"BW_SESSION": "session-token"})

    assert cache_path.read_bytes().startswith(b"gpg:")
    assert pwdmgr.load_encrypted_cache() == {"BW_SESSION": "session-token"}
    assert calls == [
        ("encrypt", b'{"BW_SESSION": "session-token"}'),
        ("decrypt", b'gpg:{"BW_SESSION": "session-token"}'),
    ]


def test_pwdmgr_clean_cache_removes_current_cache(monkeypatch, tmp_path: Path) -> None:
    tmp_results_root = tmp_path / "tmp_results"
    cache_path = tmp_results_root / "cache" / "pwdmgr" / "cache.json.gpg"

    cache_path.parent.mkdir(parents=True)
    cache_path.write_bytes(b"gpg-cache")

    monkeypatch.setattr(pwdmgr, "TMP_RESULTS_ROOT", tmp_results_root)
    monkeypatch.setattr(pwdmgr, "CACHE_PATH", cache_path)

    pwdmgr.clean_cache()

    assert not cache_path.exists()
