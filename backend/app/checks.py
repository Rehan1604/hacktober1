import re

from app.schemas import Finding

_N = r"\d+(?:\.\d+)?"
_SEP = r"(?:-|–|to)"

# "Test: X   Result: 6.8 %   Reference range: 4.0 - 5.6 %   Flag: H"
_LABELLED = re.compile(
    rf"(?:Test:\s*)?(?P<name>.+?)\s+Result:\s*(?P<val>{_N})\s*(?P<unit>\S*)\s+.*?"
    rf"Reference range:\s*(?P<lo>{_N})\s*{_SEP}\s*(?P<hi>{_N})",
    re.I,
)
# "Haemoglobin    13.9    g/dL    13.0 - 17.0    L"
_TABLE = re.compile(
    rf"^\s*(?P<name>[A-Za-z].*?)\s+(?P<val>{_N})\s*(?P<unit>[A-Za-z%/µ]\S*)?\s+"
    rf"(?P<lo>{_N})\s*{_SEP}\s*(?P<hi>{_N})(?:\s+(?P<flag>H|L|HIGH|LOW))?\s*$",
    re.I,
)
_FLAG = re.compile(r"Flag:\s*([A-Za-z]+)", re.I)


def _status(v: float, lo: float, hi: float) -> str:
    return "above" if v > hi else "below" if v < lo else "within"


def extract_findings(text: str) -> list[Finding]:
    out: list[Finding] = []
    for line in text.splitlines():
        m = _LABELLED.search(line) or _TABLE.match(line)
        if not m:
            continue
        lo, hi, val = float(m["lo"]), float(m["hi"]), float(m["val"])
        if hi <= lo:
            continue
        flag_m = _FLAG.search(line)
        flag = flag_m.group(1) if flag_m else (m.groupdict().get("flag") or "")
        out.append(Finding(
            name=m["name"].strip(" :-"), value=val, unit=(m["unit"] or "").strip(),
            low=lo, high=hi, status=_status(val, lo, hi), flag=flag.upper(),
        ))
    return out


_PHRASE = {
    "above": "above the range listed in the report",
    "below": "below the range listed in the report",
    "within": "within the range listed in the report",
}


def _line(f: Finding) -> str:
    flag = f", flag: {f.flag}" if f.flag else ""
    return (f"{f.name}: {f.value:g} {f.unit} is {_PHRASE[f.status]} "
            f"({f.low:g} - {f.high:g}{flag})").replace("  ", " ")


def facts_block(findings: list[Finding]) -> str:
    return "\n".join("- " + _line(f) for f in findings)


def key_point_lines(findings: list[Finding]) -> list[str]:
    return [_line(f) for f in findings]


def fallback_summary(findings: list[Finding]) -> str:
    out = [f for f in findings if f.status != "within"]
    if not out:
        return f"All {len(findings)} results are within the ranges listed in the report."
    names = ", ".join(f"{f.name} ({f.status} the listed range)" for f in out)
    return (f"{len(out)} of {len(findings)} results are outside the range listed in the "
            f"report: {names}.")


def specific_questions(findings: list[Finding]) -> list[str]:
    return [
        f"Ask what your {f.name} result ({f.value:g} {f.unit}, {_PHRASE[f.status]}) "
        f"means for you and whether any follow-up is needed."
        for f in findings if f.status != "within"
    ]

_PHRASE_HI = {
    "above": "रिपोर्ट में दी गई सीमा से ऊपर है",
    "below": "रिपोर्ट में दी गई सीमा से नीचे है",
    "within": "रिपोर्ट में दी गई सीमा के अंदर है",
}
_STATUS_HI = {"above": "सीमा से ऊपर", "below": "सीमा से नीचे", "within": "सीमा के अंदर"}


def key_point_lines_hi(findings: list[Finding]) -> list[str]:
    out = []
    for f in findings:
        flag = f", फ्लैग: {f.flag}" if f.flag else ""
        out.append(
            f"{f.name}: {f.value:g} {f.unit} {_PHRASE_HI[f.status]} ({f.low:g} - {f.high:g}{flag})"
            .replace("  ", " ")
        )
    return out


def summary_hi(findings: list[Finding]) -> str:
    out = [f for f in findings if f.status != "within"]
    if not out:
        return f"सभी {len(findings)} नतीजे रिपोर्ट में दी गई सीमा के अंदर हैं।"
    names = ", ".join(f"{f.name} ({_STATUS_HI[f.status]})" for f in out)
    return f"{len(findings)} में से {len(out)} नतीजे रिपोर्ट में दी गई सीमा से बाहर हैं: {names}।"


def questions_hi(findings: list[Finding]) -> list[str]:
    return [
        f"अपने डॉक्टर से पूछें कि आपके {f.name} के नतीजे ({f.value:g} {f.unit}, "
        f"{_STATUS_HI[f.status]}) का आपके लिए क्या मतलब है और क्या आगे किसी फॉलो-अप की ज़रूरत है।"
        for f in findings if f.status != "within"
    ]