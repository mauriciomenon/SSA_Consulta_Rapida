from __future__ import annotations

import pytest

from gui.ssa import system_integration


def test_validate_local_open_target_requires_allowed_base(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="Base permitida obrigatoria"):
        system_integration.validate_local_open_target(
            str(target),
            must_exist=True,
            expect_dir=False,
        )


def test_validate_local_open_target_rejects_path_outside_allowed_base(tmp_path):
    allowed = tmp_path / "allowed"
    blocked = tmp_path / "blocked"
    allowed.mkdir()
    blocked.mkdir()
    target = blocked / "file.txt"
    target.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="fora da base permitida"):
        system_integration.validate_local_open_target(
            str(target),
            must_exist=True,
            expect_dir=False,
            allowed_base=str(allowed),
        )


def test_validate_local_open_target_rejects_symlink_escape(tmp_path):
    allowed = tmp_path / "allowed"
    blocked = tmp_path / "blocked"
    allowed.mkdir()
    blocked.mkdir()
    target = blocked / "file.txt"
    target.write_text("x", encoding="utf-8")
    symlink = allowed / "linked.txt"
    symlink.symlink_to(target)

    with pytest.raises(ValueError, match="fora da base permitida"):
        system_integration.validate_local_open_target(
            str(symlink),
            must_exist=True,
            expect_dir=False,
            allowed_base=str(allowed),
        )


def test_validate_local_open_target_rejects_command_metacharacters(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    target = allowed / "bad;name.txt"
    target.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="caracteres reservados"):
        system_integration.validate_local_open_target(
            str(target),
            must_exist=True,
            expect_dir=False,
            allowed_base=str(allowed),
        )


def test_build_platform_open_args_uses_separator_outside_windows(monkeypatch):
    monkeypatch.setattr(system_integration.sys, "platform", "darwin")

    assert system_integration.build_platform_open_args("/usr/bin/open", "/tmp/a") == [
        "/usr/bin/open",
        "--",
        "/tmp/a",
    ]


def test_build_platform_open_args_keeps_windows_explorer_contract(monkeypatch):
    monkeypatch.setattr(system_integration.sys, "platform", "win32")

    assert system_integration.build_platform_open_args(
        r"C:\Windows\explorer.exe", r"C:\tmp\a"
    ) == [r"C:\Windows\explorer.exe", r"C:\tmp\a"]


def test_open_allowed_url_requires_https_and_allowed_host():
    opened = []

    class _Url:
        def __init__(self, value: str) -> None:
            self.value = value

        def scheme(self) -> str:
            return self.value.split(":", 1)[0]

        def host(self) -> str:
            if "://" not in self.value:
                return ""
            return self.value.split("://", 1)[1].split("/", 1)[0]

    class _Desktop:
        @staticmethod
        def openUrl(url: _Url) -> bool:
            opened.append(url.value)
            return True

    class _Logger:
        @staticmethod
        def warning(*_args, **_kwargs) -> None:
            return None

    assert system_integration.open_allowed_url(
        "https://osprd.itaipu/SAM_SMA/",
        qdesktopservices=_Desktop,
        qurl_cls=_Url,
        logger=_Logger,
    )
    assert not system_integration.open_allowed_url(
        "https://example.com/SAM_SMA/",
        qdesktopservices=_Desktop,
        qurl_cls=_Url,
        logger=_Logger,
    )
    assert not system_integration.open_allowed_url(
        "http://osprd.itaipu/SAM_SMA/",
        qdesktopservices=_Desktop,
        qurl_cls=_Url,
        logger=_Logger,
    )
    assert opened == ["https://osprd.itaipu/SAM_SMA/"]
