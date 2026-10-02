async function request(url, options) {
  let res;
  try {
    res = await fetch(url, options);
  } catch {
    throw new Error("Can't reach the app. Is the backend running?");
  }
  if (!res.ok) {
    let msg = `Something went wrong (${res.status}).`;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") msg = j.detail;
    } catch {}
    throw new Error(msg);
  }
  return res.status === 204 ? null : res.json();
}

export const explain = (file, text) => {
  const f = new FormData();
  if (file) f.append("file", file);
  else f.append("text", text);
  return request("/api/explain", { method: "POST", body: f });
};
export const getHindi = (id) => request(`/api/documents/${id}/hindi`, { method: "POST" });
export const listDocs = () => request("/api/documents");
export const getDoc = (id) => request(`/api/documents/${id}`);
export const sendFeedback = (id, helpful) =>
  request(`/api/documents/${id}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ helpful }),
  });
export const deleteDoc = (id) => request(`/api/documents/${id}`, { method: "DELETE" });