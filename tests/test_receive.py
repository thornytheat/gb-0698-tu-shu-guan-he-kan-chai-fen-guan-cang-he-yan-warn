# TRAP-08
# TRAP-05
# TRAP-03
# TRAP-01
from app.modules.m1_receive.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_receive_sample(result):
    assert len(result["raw"])==44

def test_receive_multiline(sample):
    from app.reader import read_rows
    rows,_,_=read_rows(sample,FIELDS)
    assert any("\n" in r["note"] for r in rows)

def test_receive_encoding(sample):
    from app.reader import decode
    assert "期刊" in decode(sample.encode("gb18030"))

def test_receive_badcols(result):
    assert any(r["reason"]=="COLUMN_COUNT" for r in result["quarantine"])

def test_receive_empty():
    with pytest.raises(BusinessError):read_rows("",FIELDS)

def test_receive_header():
    with pytest.raises(BusinessError):read_rows(",".join(FIELDS),FIELDS)

def test_receive_id(result):
    assert result["raw"][0]["record_id"]=="00001"