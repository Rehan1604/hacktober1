import { useEffect, useRef, useState } from "react";
import { deleteDoc, explain, getDoc, getHindi, listDocs, sendFeedback } from "./api";

const MAX_BYTES = 10 * 1024 * 1024;

function useElapsed(active) {
  const [s, setS] = useState(0);
  useEffect(() => {
    if (!active) return setS(0);
    const t = setInterval(() => setS((x) => x + 1), 1000);
    return () => clearInterval(t);
  }, [active]);
  return s;
}

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
  const elapsed = useElapsed(loading || hindiLoading);
  const camRef = useRef(null);
  const fileRef = useRef(null);

  const pick = (f) => {
    if (!f) return;
    if (f.size > MAX_BYTES) return setError("That file is larger than 10 MB.");
    setError("");
    setFile(f);
  };

  const submit = async () => {
    setError("");
    setLoading(true);
    try {
      const r = await explain(file, text);
      setDoc({ id: r.id, result: r.result, hindi: null, helpful: null, disclaimer: r.disclaimer });
      setLang("en");
      setView("result");
      setFile(null);
      setText("");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const showHindi = async () => {
    setError("");
    if (doc.hindi) return setLang("hi");
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
    try {
      setHistory(await listDocs());
    } catch (e) {
      setError(e.message);
    }
  };

  const openDoc = async (id) => {
    try {
      const d = await getDoc(id);
      setDoc({ id: d.id, result: d.result, hindi: d.hindi, helpful: d.helpful, disclaimer: d.disclaimer });
      setLang("en");
      setView("result");
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
      <header>
        <h1>Plain-Words</h1>
        <nav>
          <button className="link" onClick={() => { setError(""); setView("new"); }}>New</button>
          <button className="link" onClick={openHistory}>History</button>
        </nav>
      </header>

      {error && <div className="error" role="alert">{error}</div>}

      {view === "new" && (
        <main>
          <p className="lead">Add a document you find hard to understand. It is read on this computer, and nothing is sent to the internet.</p>

          <div className="row">
            <button onClick={() => camRef.current.click()}>📷 Take a photo</button>
            <button onClick={() => fileRef.current.click()}>📄 Choose a file</button>
          </div>
          <input ref={camRef} type="file" accept="image/*" capture="environment" hidden onChange={(e) => pick(e.target.files[0])} />
          <input ref={fileRef} type="file" accept=".pdf,.txt,image/*" hidden onChange={(e) => pick(e.target.files[0])} />

          {file && (
            <p className="chip">
              {file.name} <button className="link" onClick={() => setFile(null)}>remove</button>
            </p>
          )}

          <label htmlFor="t">…or paste the text</label>
          <textarea id="t" rows={7} value={text} disabled={!!file} onChange={(e) => setText(e.target.value)} placeholder="Paste the text of the report, notice or form here" />

          <button className="primary" disabled={!canSubmit} onClick={submit}>
            {loading ? `Reading… ${elapsed}s` : "Explain it"}
          </button>
          {loading && <p className="hint">This runs on a laptop without a graphics card, so it takes 30–60 seconds. Please keep this page open.</p>}
        </main>
      )}

      {view === "history" && (
        <main>
          {history.length === 0 && <p className="hint">Nothing saved yet.</p>}
          {history.map((h) => (
            <div className="card" key={h.id}>
              <button className="link left" onClick={() => openDoc(h.id)}>
                <strong>{h.doc_type}</strong> · {new Date(h.created_at).toLocaleString()}
                <span className="sub">{h.summary}</span>
              </button>
              <button className="link danger" onClick={() => remove(h.id)}>Delete</button>
            </div>
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
    </div>
  );
}

function Result({ doc, lang, setLang, showHindi, hindiLoading, elapsed, rate, remove }) {
  const r = doc.result;
  const hi = lang === "hi" && doc.hindi;
  const summary = hi ? doc.hindi.summary : r.summary;
  const points = hi ? doc.hindi.key_points : r.key_points;
  const asks = hi ? doc.hindi.ask_professional : r.ask_professional;
  const label = hi
    ? { sum: "सारांश", pts: "मुख्य बातें", terms: "शब्दों का मतलब", ask: "अपने डॉक्टर या विशेषज्ञ से पूछें" }
    : { sum: "Summary", pts: "Key points", terms: "Words explained", ask: "Ask your doctor or the issuing office" };
  const outside = (i) => r.findings && r.findings[i] && r.findings[i].status !== "within";

  return (
    <main>
      <div className="row">
        <button className={lang === "en" ? "on" : ""} onClick={() => setLang("en")}>English</button>
        <button className={lang === "hi" ? "on" : ""} onClick={showHindi} disabled={hindiLoading}>
          {hindiLoading ? `${elapsed}s…` : "हिन्दी"}
        </button>
      </div>
      {hindiLoading && <p className="hint">Translating on this computer, about 20 seconds.</p>}

      <h2>{label.sum}</h2>
      <p>{summary}</p>

      <h2>{label.pts}</h2>
      <ul className="points">
        {points.map((p, i) => (
          <li key={i} className={outside(i) ? "out" : ""}>{p}</li>
        ))}
      </ul>

      {r.terms.length > 0 && (
        <>
          <h2>{label.terms}</h2>
          {r.terms.map((t, i) => (
            <div className="card col" key={i}>
              <strong>{t.term}</strong>
              <span>{hi && doc.hindi.term_meanings[i] ? doc.hindi.term_meanings[i] : t.meaning}</span>
              {!t.verified && <span className="sub">Could not find this wording in your document.</span>}
            </div>
          ))}
          {hi && doc.hindi.term_meanings.length === 0 && (
            <p className="hint">The Hindi for these words could not be checked, so English is shown.</p>
          )}
        </>
      )}

      <h2>{label.ask}</h2>
      <ul>
        {asks.map((a, i) => <li key={i}>{a}</li>)}
      </ul>

      <p className="disclaimer">{doc.disclaimer}</p>

      <div className="card col">
        <strong>Was this clear?</strong>
        <div className="row">
          <button className={doc.helpful === 1 ? "on" : ""} onClick={() => rate(true)}>👍 Yes</button>
          <button className={doc.helpful === 0 ? "on" : ""} onClick={() => rate(false)}>👎 No</button>
        </div>
      </div>
      <button className="link danger" onClick={remove}>Delete this document</button>
    </main>
  );
}