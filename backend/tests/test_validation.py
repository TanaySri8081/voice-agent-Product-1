from backend.routes.phone_numbers import PHONE_RE


def test_phone_regex_accepts_valid():
    for n in ["+14155550100", "14155550100", "+919876543210", "+447911123456"]:
        assert PHONE_RE.match(n), n


def test_phone_regex_rejects_invalid():
    for n in ["abc", "+1", "", "123", "+0123456789", "+1 415 555 0100", "phone-number"]:
        assert not PHONE_RE.match(n), n
