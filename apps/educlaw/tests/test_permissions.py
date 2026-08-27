import pytest

from educlaw.permissions.gate import PermissionAction, PermissionGate, classify_command


def test_classify_destructive() -> None:
    assert classify_command("rm -rf /tmp/foo") == "destructive"
    assert classify_command("git reset --hard") == "destructive"
    assert classify_command("ls -la") == "bash"


def test_default_asks_risky_not_writes() -> None:
    gate = PermissionGate(mode="default")
    assert not gate.needs_approval(PermissionAction("read", "r"))
    assert not gate.needs_approval(PermissionAction("write", "w"))
    assert gate.needs_approval(PermissionAction("bash", "b"))
    assert gate.needs_approval(PermissionAction("render", "r"))
    assert gate.needs_approval(PermissionAction("destructive", "d"))


def test_edit_asks_writes() -> None:
    gate = PermissionGate(mode="edit")
    assert gate.needs_approval(PermissionAction("write", "w"))
    assert not gate.needs_approval(PermissionAction("read", "r"))


def test_auto_never_asks() -> None:
    gate = PermissionGate(mode="auto")
    assert not gate.needs_approval(PermissionAction("destructive", "d"))


@pytest.mark.asyncio
async def test_resolver_used() -> None:
    async def deny(_action):
        return False

    gate = PermissionGate(mode="default", resolver=deny)
    allowed = await gate.approve(PermissionAction("bash", "ls"))
    assert allowed is False
