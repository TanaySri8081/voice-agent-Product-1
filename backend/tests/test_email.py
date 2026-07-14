from backend.services import email as email_mod


def test_email_mock_mode_returns_false(monkeypatch):
    # With no SMTP host configured, send_email must not attempt delivery.
    monkeypatch.setattr(email_mod.settings, "SMTP_HOST", "")
    assert email_mod.send_email("recipient", "Subject", "Body") is False
