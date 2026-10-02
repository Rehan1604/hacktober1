from app.checks import (extract_findings, key_point_lines_hi, questions_hi,
                        summary_hi)

TEXT = """Test: HbA1c   Result: 6.8 %   Reference range: 4.0 - 5.6 %   Flag: H
Test: Haemoglobin   Result: 13.9 g/dL   Reference range: 13.0 - 17.0 g/dL"""


def test_hindi_templates_cover_every_finding():
    f = extract_findings(TEXT)
    assert len(key_point_lines_hi(f)) == len(f) == 2
    assert len(questions_hi(f)) == 1  # only the out-of-range one
    assert "1" in summary_hi(f) and "2" in summary_hi(f)