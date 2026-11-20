from app.modules.m3_issues.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_issue_combined():
    assert expand("1-3")==["1","2","3"]

def test_issue_slash():
    assert expand("4/3")==["3","4"]

def test_issue_supplement():
    assert expand("s1")==["S1"]

def test_issue_reverse():
    with pytest.raises(BusinessError):expand("4-2")

def test_issue_no_guess():
    with pytest.raises(BusinessError):expand("春季号")

def test_issue_sample(result):
    assert len(result["expanded"])==42

def test_issue_fullwidth():
    assert expand("１－２")==["1","2"]
def test_missing_binding_isolated(sample):
    from app.pipeline import run
    data=sample+'\nBINDLESS,数据工程月刊,1000-0001,2026,001,12,02,,held,\n'
    r=run(data)
    assert any(x['reason']=='BINDING_REQUIRED' for x in r['quarantine'])
    assert r['books']==40
