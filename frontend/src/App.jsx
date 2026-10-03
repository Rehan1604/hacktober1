import { useEffect, useRef, useState } from "react";
import { deleteDoc, explain, getDoc, getHindi, listDocs, sendFeedback } from "./api";

const HOSTED = import.meta.env.VITE_HOSTED === "true";
const MAX_BYTES = 10 * 1024 * 1024;

const SAMPLE = `SAMPLE REPORT - FICTIONAL DATA FOR TESTING ONLY
Patient: Test Patient   Age: 45   Sex: M
Test: Glycosylated Haemoglobin (HbA1c)   Result: 6.8 %   Reference range: 4.0 - 5.6 %   Flag: H
Test: Fasting Plasma Glucose   Result: 128 mg/dL   Reference range: 70 - 99 mg/dL   Flag: H
Test: Haemoglobin   Result: 13.9 g/dL   Reference range: 13.0 - 17.0 g/dL
Remarks: Please correlate clinically. Advised follow-up with treating physician.`;

const T = {
  en: {
    sum: "Summary",
    res: "Your results",
    terms: "Words explained",
    ask: "Ask your doctor or the issuing office",
    notDx: "These are not a diagnosis. They are things worth talking to a doctor about.",
    outside: "outside the listed range",
    within: "within the listed range",
    range: "Listed range",
    status: { above: "Above listed range", below: "Below listed range", within: "Within listed range" },
  },
  hi: {
    sum: "सारांश",
    res: "आपके नतीजे",
    terms: "शब्दों का मतलब",
    ask: "अपने डॉक्टर या विशेषज्ञ से पूछें",
    notDx: "ये कोई निदान नहीं हैं। ये ऐसी बातें हैं जिन पर डॉक्टर से बात करना ठीक रहेगा।",
    outside: "सीमा से बाहर",
    within: "सीमा के अंदर",
    range: "रिपोर्ट में दी गई सीमा",
    status: { above: "सीमा से ऊपर", below: "सीमा से नीचे", within: "सीमा के अंदर" },
  },
};

const fmt = (n) => (Number.isInteger(n) ? String(n) : String(+Number(n).toFixed(2)));

function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
  } catch {
    return iso;
  }
}

function useElapsed(active) {
  const [s, setS] = useState(0);
  useEffect(() => {
    if (!active) {
      setS(0);
      return undefined;
    }
    const id = setInterval(() => setS((x) => x + 1), 1000);
    return () => clearInterval(id);
  }, [active]);
  return s;
}

const CameraIcon = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M4 8h3l1.5-2h7L17 8h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z" />
    <circle cx="12" cy="13.5" r="3.5" />
  </svg>
);

const FileIcon = () => (
  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M7 3h7l5 5v13H7z" />
    <path d="M14 3v5h5" />
    <path d="M10 13h6M10 17h6" />
  </svg>
);

export default function App() {
  const [view, setView] = useState("new"); // new | result | history
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [doc, setDoc] = useState(null);
  const [lang, setLang] = useState("en");
  const [hindiLoading, setHindiLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const elapsed = useElapsed(loading || hindiLoading);
  const camRef = useRef(null);
  const fileRef = useRef(null);

  const go = (v) => {
    setError("");
    setView(v);
  };

  const pick = (f) => {
    if (!f) return;
    if (f.size > MAX_BYTES) {
      setError("That file is larger than 10 MB.");
      return;
    }
    setError("");
    setFile(f);
    setText("");
  };

  const submit = async () => {
    setError("");
    setLoading(true);
    try {
      const r = await explain(file, text);
      setDoc({
        id: r.id,
        result: r.result,
        hindi: null,
        helpful: null,
        disclaimer: r.disclaimer,
        source: r.source,
        extracted: r.extracted_text,
      });
      setLang("en");
      setView("result");
      setFile(null);
      setText("");
      window.scrollTo({ top: 0 });
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const showHindi = async () => {
    setError("");
    if (doc.hindi) {
      setLang("hi");
      return;
    }
    setHindiLoading(true);
    try {
      const r = await getHindi(doc.id);
      setDoc((d) => ({ ...d, hindi: r.hindi }));
      setLang("hi");
    } catch (e) {
      setError(e.message);
    } finally {
      setHindiLoading(false);
    }
  };

  const rate = async (helpful) => {
    try {
      await sendFeedback(doc.id, helpful);
      setDoc((d) => ({ ...d, helpful: helpful ? 1 : 0 }));
    } catch (e) {
      setError(e.message);
    }
  };

  const openHistory = async () => {
    setError("");
    setView("history");
    setHistoryLoading(true);
    try {
      setHistory(await listDocs());
    } catch (e) {
      setError(e.message);
    } finally {
      setHistoryLoading(false);
    }
  };

  const openDoc = async (id) => {
    setError("");
    try {
      const d = await getDoc(id);
      setDoc({
        id: d.id,
        result: d.result,
        hindi: d.hindi,
        helpful: d.helpful,
        disclaimer: d.disclaimer,
        source: d.source_type,
        extracted: d.source_type === "image" ? d.original_text : null,
      });
      setLang("en");
      setView("result");
      window.scrollTo({ top: 0 });
    } catch (e) {
      setError(e.message);
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this document and its explanation?")) return;
    try {
      await deleteDoc(id);
      setHistory((h) => h.filter((x) => x.id !== id));
      if (doc && doc.id === id) setDoc(null);
      if (view === "result") setView("new");
    } catch (e) {
      setError(e.message);
    }
  };

  const canSubmit = !loading && (file || text.trim().length > 0);

  return (
    <div className="app">
      <header className="top">
        <button className="brand" onClick={() => go("new")} aria-label="Plain-Words home">
          <span className="mark" aria-hidden="true">P</span>
          <span className="brand-name">Plain<em>·</em>Words</span>
        </button>
        <nav aria-label="Main">
          <button className={`tab ${view === "new" ? "on" : ""}`} aria-current={view === "new" ? "page" : undefined} onClick={() => go("new")}>
            New
          </button>
          <button className={`tab ${view === "history" ? "on" : ""}`} aria-current={view === "history" ? "page" : undefined} onClick={openHistory}>
            History
          </button>
        </nav>
      </header>

      {HOSTED && (
        <div className="notice" role="note">
          <strong>Hosted demo.</strong> Text you submit here is sent to a server and to an AI provider (Groq). Use only the sample report or non-personal text. For private use, run the app locally.
        </div>
      )}

      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}

      {view === "new" && (
        <main className="fade">
          <section className="hero">
            <span className={`pill ${HOSTED ? "cloud" : "local"}`}>
              {HOSTED ? "Hosted demo · sample text only" : "Runs on this computer · nothing leaves it"}
            </span>
            <h1>
              Paperwork, <span className="hl">in plain words.</span>
            </h1>
            <p className="lede">
              Add a photo, PDF or pasted text. Get a calm explanation in English and Hindi, with the numbers checked against the ranges printed on the document.
            </p>
          </section>

          <section className="card" aria-label="Add a document">
            <div className="pick">
              <button className="pick-btn" onClick={() => camRef.current.click()}>
                <CameraIcon />
                <span>Take a photo</span>
              </button>
              <button className="pick-btn" onClick={() => fileRef.current.click()}>
                <FileIcon />
                <span>Choose a file</span>
              </button>
            </div>
            <input ref={camRef} type="file" accept="image/*" capture="environment" hidden onChange={(e) => pick(e.target.files[0])} />
            <input ref={fileRef} type="file" accept=".pdf,.txt,image/*" hidden onChange={(e) => pick(e.target.files[0])} />
            {HOSTED && <p className="hint">Photo reading may be unavailable in this hosted demo. Pasted text and PDFs work.</p>}

            {file && (
              <div className="chip">
                <span className="chip-name">{file.name}</span>
                <button className="link" onClick={() => setFile(null)}>
                  Remove
                </button>
              </div>
            )}

            <div className="divider">
              <span>or paste the text</span>
            </div>

            <label className="sr" htmlFor="t">
              Document text
            </label>
            <textarea
              id="t"
              rows={7}
              value={text}
              disabled={!!file}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste the text of the report, notice or form here"
            />
            <div className="row-between">
              <button className="link" onClick={() => { setFile(null); setText(SAMPLE); }}>
                Try the fictional sample report
              </button>
              {text && (
                <button className="link muted" onClick={() => setText("")}>
                  Clear
                </button>
              )}
            </div>

            <button className="btn primary big" disabled={!canSubmit} onClick={submit}>
              {loading ? `Reading… ${elapsed}s` : "Explain it"}
            </button>

            {loading && (
              <div className="working" aria-live="polite">
                <div className="spinner" aria-hidden="true" />
                <div className="working-body">
                  <p>
                    <strong>Still working. It has not frozen.</strong> {file ? "It reads the photo first, then explains it. " : ""}
                    {HOSTED ? "This can take up to a minute if the server was asleep." : "This runs on a laptop, so it takes about a minute."} Please keep this page open.
                  </p>
                  <div className="bar" aria-hidden="true">
                    <span />
                  </div>
                </div>
              </div>
            )}
          </section>

          <ul className="trust">
            <li>Numbers are compared by code, not guessed by the model.</li>
            <li>Not medical, legal or financial advice. It explains what a document says.</li>
          </ul>
        </main>
      )}

      {view === "history" && (
        <main className="fade">
          <h2 className="page-title">History</h2>
          {historyLoading && <p className="hint">Loading…</p>}
          {!historyLoading && history.length === 0 && (
            <div className="empty">
              <p>Nothing saved yet.</p>
              <button className="btn" onClick={() => go("new")}>
                Explain a document
              </button>
            </div>
          )}
          {history.map((h) => (
            <article className="card hist" key={h.id}>
              <button className="hist-main" onClick={() => openDoc(h.id)}>
                <span className="hist-top">
                  <strong>{h.doc_type}</strong>
                  <span className="muted">{fmtDate(h.created_at)}</span>
                </span>
                <span className="hist-sum">{h.summary}</span>
              </button>
              <button className="link danger" onClick={() => remove(h.id)}>
                Delete
              </button>
            </article>
          ))}
        </main>
      )}

      {view === "result" && doc && (
        <Result
          doc={doc}
          lang={lang}
          setLang={setLang}
          showHindi={showHindi}
          hindiLoading={hindiLoading}
          elapsed={elapsed}
          rate={rate}
          remove={() => remove(doc.id)}
        />
      )}

      <footer className="foot">
        Built for a friend · open-weight AI · not a substitute for a professional
      </footer>
    </div>
  );
}

function RangeBar({ f, caption }) {
  const span = f.high - f.low || 1;
  const min = Math.min(f.low, f.value) - span * 0.35;
  const max = Math.max(f.high, f.value) + span * 0.35;
  const pct = (x) => ((x - min) / (max - min)) * 100;
  return (
    <div className="rb">
      <div
        className="rb-track"
        role="img"
        aria-label={`${fmt(f.value)} ${f.unit}. Listed range ${fmt(f.low)} to ${fmt(f.high)}.`}
      >
        <div className="rb-band" style={{ left: `${pct(f.low)}%`, width: `${pct(f.high) - pct(f.low)}%` }} />
        <div className={`rb-dot ${f.status}`} style={{ left: `${pct(f.value)}%` }} />
      </div>
      <p className="rb-cap">{caption}</p>
    </div>
  );
}

function Result({ doc, lang, setLang, showHindi, hindiLoading, elapsed, rate, remove }) {
  const r = doc.result;
  const hi = lang === "hi" && !!doc.hindi;
  const t = hi ? T.hi : T.en;
  const summary = hi ? doc.hindi.summary : r.summary;
  const points = hi ? doc.hindi.key_points : r.key_points;
  const asks = hi ? doc.hindi.ask_professional : r.ask_professional;
  const findings = r.findings || [];
  const outCount = findings.filter((f) => f.status !== "within").length;
  const inCount = findings.length - outCount;

  return (
    <main className="fade">
      <div className="seg" role="group" aria-label="Language">
        <button aria-pressed={lang === "en"} className={lang === "en" ? "on" : ""} onClick={() => setLang("en")}>
          English
        </button>
        <button aria-pressed={lang === "hi"} className={lang === "hi" ? "on" : ""} onClick={showHindi} disabled={hindiLoading}>
          {hindiLoading ? `${elapsed}s…` : "हिन्दी"}
        </button>
      </div>
      {hindiLoading && <p className="hint">Translating, about 20 seconds.</p>}

      {doc.source === "image" && doc.extracted && (
        <details className="ocr">
          <summary>Photos can be misread. Check what was read from your photo</summary>
          <pre>{doc.extracted}</pre>
          <p className="hint">Compare these numbers with your paper report. If one looks wrong, retake the photo.</p>
        </details>
      )}

      <section className="card summary">
        <span className="chip small">{r.doc_type}</span>
        <h2 className="sec">{t.sum}</h2>
        <p className="lead-text">{summary}</p>
        {findings.length > 0 && (
          <div className="stats">
            <div className="stat warn">
              <b>{outCount}</b>
              <span>{t.outside}</span>
            </div>
            <div className="stat ok">
              <b>{inCount}</b>
              <span>{t.within}</span>
            </div>
          </div>
        )}
      </section>

      <h2 className="sec">{t.res}</h2>
      {points.map((p, i) => {
        const f = findings[i];
        if (!f) {
          return (
            <article className="finding plain" key={i}>
              <p className="finding-text">{p}</p>
            </article>
          );
        }
        return (
          <article className={`finding ${f.status}`} key={i}>
            <div className="finding-top">
              <div>
                <div className="finding-name">{f.name}</div>
                <div className="finding-value">
                  {fmt(f.value)} <span>{f.unit}</span>
                </div>
              </div>
              <span className={`badge ${f.status}`}>{t.status[f.status]}</span>
            </div>
            <RangeBar f={f} caption={`${t.range}: ${fmt(f.low)} – ${fmt(f.high)} ${f.unit}`} />
            <p className="finding-text">{p}</p>
          </article>
        );
      })}

      {r.terms.length > 0 && (
        <>
          <h2 className="sec">{t.terms}</h2>
          {r.terms.map((term, i) => (
            <article className="term" key={i}>
              <strong>{term.term}</strong>
              <span>{hi && doc.hindi.term_meanings[i] ? doc.hindi.term_meanings[i] : term.meaning}</span>
              {!term.verified && <span className="sub">Could not find this wording in your document.</span>}
            </article>
          ))}
          {hi && doc.hindi.term_meanings.length === 0 && (
            <p className="hint">The Hindi for these words could not be checked, so English is shown.</p>
          )}
        </>
      )}

      <section className="card ask">
        <h2 className="sec">{t.ask}</h2>
        <p className="hint">{t.notDx}</p>
        <ul>
          {asks.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ul>
      </section>

      <p className="disclaimer">{doc.disclaimer}</p>

      <section className="card feedback">
        <strong>Was this clear?</strong>
        <div className="seg">
          <button className={doc.helpful === 1 ? "on" : ""} aria-pressed={doc.helpful === 1} onClick={() => rate(true)}>
            👍 Yes
          </button>
          <button className={doc.helpful === 0 ? "on" : ""} aria-pressed={doc.helpful === 0} onClick={() => rate(false)}>
            👎 No
          </button>
        </div>
      </section>

      <button className="link danger" onClick={remove}>
        Delete this document
      </button>
    </main>
  );
}