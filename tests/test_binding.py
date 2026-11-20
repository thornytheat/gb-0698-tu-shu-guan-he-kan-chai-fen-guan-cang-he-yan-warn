from app.modules.m6_binding.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_binding_sample(result):
    assert result["books"]==40

def test_binding_row_balance(result):
    assert result["balance"]["input"]==47

def test_binding_quarantine(result):
    assert result["balance"]["quarantined"]==4

def test_binding_empty():
    assert book_count([])==0

def test_binding_same_book():
    r={"journal_key":"i","year":"2026","copy":"01","binding":"a","status":"held"}
    assert book_count([r,r])==1

def test_binding_different_copy():
    r={"journal_key":"i","year":"2026","copy":"01","binding":"a","status":"held"}
    assert book_count([r,dict(r,copy="02")])==2

def test_binding_suspend_excluded():
    assert book_count([{"status":"suspended"}])==0