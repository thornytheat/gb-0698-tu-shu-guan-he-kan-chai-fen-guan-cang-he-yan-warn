from app.modules.m7_supplement.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_supplement_plan():
    assert request_list([{"issn":"i","title":"a","year":"2026","missing":["2","3"]}])[1]["issue"]=="3"

def test_supplement_empty():
    assert request_list([])==[]

def test_supplement_covered():
    assert request_list([{"missing":[]}])==[]

def test_supplement_sample(result):
    assert len(result["final"])>0

def test_supplement_clear(result):
    assert result["blocked"] is False

def test_supplement_unique(result):
    assert len({(r["issn"],r["year"],r["issue"]) for r in result["final"]})==len(result["final"])

def test_supplement_status(result):
    assert all(r["status"]=="待补录" for r in result["final"])