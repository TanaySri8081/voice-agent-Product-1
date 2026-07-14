import json
import uuid
from datetime import datetime

from backend.utils.helpers import to_uuid, serialize_model, serialize_models, api_response
from backend.models import Tenant


def test_to_uuid():
    u = uuid.uuid4()
    assert to_uuid(u) == u
    assert to_uuid(str(u)) == u
    assert to_uuid("not-a-uuid") is None
    assert to_uuid(None) is None


def test_serialize_model_converts_types():
    t = Tenant(name="X", subscription="free")
    t.id = uuid.uuid4()
    t.created_at = datetime(2026, 1, 1, 12, 0, 0)
    d = serialize_model(t)
    assert d["name"] == "X"
    assert d["id"] == str(t.id)  # UUID -> str
    assert d["created_at"] == "2026-01-01T12:00:00"  # datetime -> ISO
    assert serialize_model(None) is None
    assert serialize_models([t, None]) == [serialize_model(t)]


def test_api_response_envelope():
    r = api_response(success=True, message="ok", data={"a": 1})
    assert r.status_code == 200
    body = json.loads(r.body.decode())
    assert body == {"success": True, "message": "ok", "data": {"a": 1}, "error": None}

    r2 = api_response(success=False, message="bad", status_code=400)
    assert r2.status_code == 400
    body2 = json.loads(r2.body.decode())
    assert body2["success"] is False and body2["data"] is None
