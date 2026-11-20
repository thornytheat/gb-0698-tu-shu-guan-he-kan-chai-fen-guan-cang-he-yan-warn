# TRAP-14
from app.modules.m4_combined.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_combined_sample(result):
    assert len(result["held"])==40

def test_combined_physical(result):
    assert any(r["physical_books"]==1 and r["covered_issues"]==2 for r in result["held"])

def test_combined_no_conflicts(result):
    assert result["binding_conflicts"]==[]

def test_combined_duplicate():
    r={"journal_key":"i","year":"2026","issues":["1"],"copy":"01","binding":"a","record_id":"1","status":"held"}
    assert collisions([r,dict(r,binding="b",record_id="2")])[0]["reason"]=="BINDING_CONFLICT"

def test_combined_copies():
    r={"journal_key":"i","year":"2026","issues":["1"],"copy":"01","binding":"a","record_id":"1","status":"held"}
    assert collisions([r,dict(r,copy="02",binding="b")])==[]

def test_combined_missing():
    assert collisions([])==[]

def test_combined_same_bind():
    r={"journal_key":"i","year":"2026","issues":["1"],"copy":"01","binding":"a","record_id":"1","status":"held"}
    assert collisions([r,r])==[]