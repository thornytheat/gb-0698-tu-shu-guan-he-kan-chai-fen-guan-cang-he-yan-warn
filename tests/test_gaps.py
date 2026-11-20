# TRAP-23
from app.modules.m5_gaps.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_gap_suspended():
    assert missing(["1","2"],["3"],4)==["4"]

def test_gap_supplement():
    assert missing(["S1"],[],2)==["1","2"]

def test_gap_complete():
    assert missing(["1","2"],[],2)==[]

def test_gap_empty():
    assert missing([],[],2)==["1","2"]

def test_gap_sample(result):
    assert len(result["gaps"])==4

def test_gap_expected(result):
    assert any(r["status"]=="GAP" for r in result["gaps"])

def test_gap_no_suspended(result):
    assert all("12" not in r["missing"] for r in result["gaps"] if "12" in r["suspended"])