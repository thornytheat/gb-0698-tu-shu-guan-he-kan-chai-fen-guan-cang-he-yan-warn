from app.errors import BusinessError
from app.modules.m8_donation import store


def _text(payload, field):
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise BusinessError(field.upper(), f"缺少{field}或类型错误")
    return value.strip()


def register_library(payload):
    name = _text(payload, "name")
    gaps = payload.get("gaps") or []
    if not isinstance(gaps, list):
        raise BusinessError("GAPS", "缺期须为列表")
    text = payload.get("text")
    if text is not None and not isinstance(text, str):
        raise BusinessError("TEXT", "输入须为文本")
    return store.register_library(name, gaps=gaps, text=text)


def register_donation(payload):
    return store.register_donation(
        _text(payload, "issn"), _text(payload, "title"), _text(payload, "year"),
        payload.get("issues"), payload.get("donor", ""))


def claim(payload):
    return store.claim(_text(payload, "donation_id"), _text(payload, "library_id"))


def confirm(payload):
    revision = payload.get("revision")
    if type(revision) is not int:
        raise BusinessError("REVISION", "版本须为整数")
    return store.confirm(_text(payload, "donation_id"), _text(payload, "claim_id"), revision)


def arrive(payload):
    return store.arrive(_text(payload, "donation_id"))


def overview():
    return store.overview()
