import json
import re

from pydantic import ValidationError

from app.checks import (extract_findings, facts_block, fallback_summary,
                        key_point_lines, key_point_lines_hi, questions_hi,
                        specific_questions, summary_hi)
from app.llm import LLMProvider, LLMRetryable
from app.prompts import (EXPLAIN_SYSTEM, TERMS_SYSTEM, TRANSLATE_SYSTEM,
                         TRANSLATE_TERMS_SYSTEM)
from app.schemas import Explanation, HindiVersion, TermMeaningsHi, TermsOnly

MAX_CHARS = 6000

FORBIDDEN = [
    "within the reference range", "within the normal range", "within normal",
    "within the range", "within range", "is normal", "are normal",
    "pre-diabetes", "prediabetes", "diabetic", "diabetes",
]

GENERIC_QUESTION = "If anything here is unclear, ask your doctor or the lab that issued the report."
GENERIC_QUESTION_HI = "अगर कुछ भी समझ न आए, तो अपने डॉक्टर या रिपोर्ट जारी करने वाली लैब से पूछें।"

class ExplainError(Exception):
    pass


class DocumentTooLong(ExplainError):
    pass


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _verify_terms(exp: Explanation, text: str) -> Explanation:
    haystack = _norm(text)
    for t in exp.terms:
        t.verified = bool(t.source_line.strip()) and _norm(t.source_line) in haystack
    return exp


def _contradiction(exp: Explanation, findings, text: str):
    if not any(f.status != "within" for f in findings):
        return None
    doc = _norm(text)
    blob = _norm(exp.summary + " " + " ".join(exp.key_points))
    for p in FORBIDDEN:
        if p in blob and p not in doc:
            return (f'You wrote "{p}", but some results are outside the listed range. '
                    "Follow the FACTS exactly.")
    return None


async def _json_call(provider: LLMProvider, system: str, user: str, model_cls,
                     check=None, attempts: int = 2):
    prompt, last_err, obj = user, None, None
    for _ in range(attempts):
        try:
            raw = await provider.generate(system, prompt, json_mode=True)
        except LLMRetryable as e:
            last_err = e
            continue
        try:
            obj = model_cls.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = e
            prompt = user + "\n\nYour previous reply was not valid JSON in the required shape. Reply with ONLY the JSON object."
            continue
        problem = check(obj) if check else None
        if not problem:
            return obj
        prompt = user + f"\n\nCORRECTION: {problem}"
    if obj is not None:
        return obj
    raise ExplainError(f"The model returned unusable output: {last_err}")


async def explain(text: str, provider: LLMProvider) -> Explanation:
    text = text.strip()
    if len(text) < 20:
        raise ExplainError("The document is empty or too short to explain.")
    if len(text) > MAX_CHARS:
        raise DocumentTooLong(f"Document is {len(text)} characters; the limit is {MAX_CHARS}.")

    findings = extract_findings(text)
    doc_block = f'DOCUMENT:\n"""\n{text}\n"""'

    if findings:
        # Numbers are judged by code. The model only writes the glossary.
        t = await _json_call(provider, TERMS_SYSTEM, doc_block, TermsOnly)
        exp = Explanation(
            doc_type=t.doc_type,
            summary=fallback_summary(findings),
            key_points=key_point_lines(findings),
            terms=t.terms,
            ask_professional=specific_questions(findings) or [GENERIC_QUESTION],
            findings=findings,
        )
        return _verify_terms(exp, text)

    # No numbers to check (notice, bill, form): the model writes the summary.
    exp = await _json_call(provider, EXPLAIN_SYSTEM, doc_block, Explanation)
    return _verify_terms(exp, text)


async def to_hindi(exp: Explanation, provider: LLMProvider) -> HindiVersion:
    if exp.findings:
        # Computed sentences use fixed Hindi templates; the model only translates the glossary.
        meanings = [t.meaning for t in exp.terms]
        translated: list[str] = []
        if meanings:
            payload = json.dumps({"term_meanings": meanings}, ensure_ascii=False)
            r = await _json_call(provider, TRANSLATE_TERMS_SYSTEM, payload, TermMeaningsHi)
            translated = r.term_meanings if len(r.term_meanings) == len(meanings) else []
        return HindiVersion(
            summary=summary_hi(exp.findings),
            key_points=key_point_lines_hi(exp.findings),
            ask_professional=questions_hi(exp.findings) or [GENERIC_QUESTION_HI],
            term_meanings=translated,
        )

    payload = json.dumps(
        {
            "summary": exp.summary,
            "key_points": exp.key_points,
            "ask_professional": exp.ask_professional,
            "term_meanings": [t.meaning for t in exp.terms],
        },
        ensure_ascii=False,
    )
    hv = await _json_call(provider, TRANSLATE_SYSTEM, payload, HindiVersion)
    if len(hv.term_meanings) != len(exp.terms):
        hv.term_meanings = []
    return hv