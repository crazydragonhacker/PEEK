import pytest

from app.models import AllotmentStatus
from app.registrars.kfintech import KFintechAdapter
from app.registrars.linkintime import LinkIntimeAdapter, parse_dataset


def test_kfin_allotted():
    result = KFintechAdapter._parse({"data": [{"All_Shares": "20", "App_Shares": "100", "Name": "Test"}]})
    assert result.status is AllotmentStatus.ALLOTTED
    assert result.shares_allotted == 20


def test_kfin_not_allotted():
    result = KFintechAdapter._parse({"data": [{"All_Shares": "0", "App_Shares": "100", "Name": "Test"}]})
    assert result.status is AllotmentStatus.NOT_ALLOTTED


def test_kfin_empty_is_not_applied():
    result = KFintechAdapter._parse({"data": []})
    assert result.status is AllotmentStatus.NOT_APPLIED


def test_kfin_unknown_schema_is_failure():
    result = KFintechAdapter._parse({"data": [{"Name": "Test"}]})
    assert result.status is AllotmentStatus.LOOKUP_FAILED


def test_mufg_dataset_parser():
    xml = "<NewDataSet><Table><company_id>123</company_id><companyname>Example IPO</companyname></Table></NewDataSet>"
    assert parse_dataset(xml) == [{"company_id": "123", "companyname": "Example IPO"}]


def test_mufg_empty_dataset_is_not_applied():
    adapter = LinkIntimeAdapter()
    result = adapter._parse_result([])
    assert result.status is AllotmentStatus.NOT_APPLIED


def test_mufg_share_parser_not_allotted():
    # Exercise the actual response parser through a tiny subclass helper added below.
    adapter = LinkIntimeAdapter()
    result = adapter._parse_result([{"Name": "Test", "Alloted_Shares": "0"}])
    assert result.status is AllotmentStatus.NOT_ALLOTTED
