# TRAP-22
# TRAP-17
from app.modules.m2_titles.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_title_alias():
    assert canonical("数据工程","1000-0001")[0]=="数据工程月刊"

def test_title_spaces():
    assert canonical(" 数据 工程月刊 ","1000-0001")[0]=="数据工程月刊"

def test_title_issn():
    with pytest.raises(BusinessError):canonical("a","bad")

def test_title_identity(result):
    assert result["identity_conflicts"]==[]

def test_title_sample(result):
    assert len(result["canonical"])==43

def test_title_zero(result):
    assert result["canonical"][0]["record_id"]=="00001"

def test_title_distinct():
    assert canonical("另一刊物","1000-0002")[0]=="另一刊物"