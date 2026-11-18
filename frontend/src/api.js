const storage = {
  get(k) {
    try {
      return sessionStorage.getItem(k);
    } catch {
      return null;
    }
  },
  set(k, v) {
    try {
      sessionStorage.setItem(k, v);
    } catch {
      /* cookies remain available */
    }
  },
};
export { storage };
export async function request(path, method = "GET", payload) {
  const headers = { "X-Buro-Request": "1" };
  if (method !== "GET") headers["Content-Type"] = "application/json";
  const token = storage.get("buro-demo-session");
  if (token) headers["X-Demo-Session"] = token;
  let r;
  try {
    r = await fetch("/api" + path, {
      method,
      headers,
      credentials: "same-origin",
      body: method === "GET" ? undefined : JSON.stringify(payload || {}),
    });
  } catch {
    throw new Error(
      "Нет соединения с кабинетом. Проверьте сеть и попробуйте ещё раз.",
    );
  }
  if (!r.ok) {
    const info = await r.json().catch(() => ({}));
    throw new Error(
      info.error || "Не удалось выполнить запрос. Попробуйте ещё раз.",
    );
  }
  if (path === "/clients/export") return r.blob();
  const data = await r.json();
  if (data.demoSession) storage.set("buro-demo-session", data.demoSession);
  return data;
}
