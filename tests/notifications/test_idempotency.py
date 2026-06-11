import json

from email.notifications.idempotency import EmailCheckpointStore


def test_checkpoint_marks_and_reads_sent_key(tmp_path) -> None:
    checkpoint_path = tmp_path / "email_checkpoint.json"
    store = EmailCheckpointStore(checkpoint_path)

    assert store.has_sent("run-1:success") is False

    store.mark_sent("run-1:success")

    assert store.has_sent("run-1:success") is True


def test_checkpoint_writes_json_atomically(tmp_path) -> None:
    checkpoint_path = tmp_path / "email_checkpoint.json"
    store = EmailCheckpointStore(checkpoint_path)

    store.mark_sent("run-1:no-data")

    checkpoint_data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert "run-1:no-data" in checkpoint_data["sent_email_keys"]
