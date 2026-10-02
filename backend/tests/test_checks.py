from app.checks import extract_findings

LABELLED = """Test: Glycosylated Haemoglobin (HbA1c)   Result: 6.8 %   Reference range: 4.0 - 5.6 %   Flag: H
Test: Fasting Plasma Glucose   Result: 128 mg/dL   Reference range: 70 - 99 mg/dL   Flag: H
Test: Haemoglobin   Result: 13.9 g/dL   Reference range: 13.0 - 17.0 g/dL"""


def test_labelled_format():
    f = extract_findings(LABELLED)
    assert [x.status for x in f] == ["above", "above", "within"]
    assert f[0].value == 6.8 and f[0].flag == "H"


def test_table_format_below():
    f = extract_findings("Haemoglobin    10.2    g/dL    13.0 - 17.0    L")
    assert len(f) == 1 and f[0].status == "below"


def test_no_values_returns_empty():
    assert extract_findings("Please pay the amount by 5 March to avoid penalty.") == []


def test_empty_and_bad_range():
    assert extract_findings("") == []
    assert extract_findings("Test: X   Result: 5   Reference range: 9 - 3") == []