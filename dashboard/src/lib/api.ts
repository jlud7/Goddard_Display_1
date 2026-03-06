const DEFAULT_TIMEOUT = 10000;
const DEFAULT_LONG_TIMEOUT = 120000;

export async function postJson(
  url: string,
  body: Record<string, unknown>,
  options?: { timeoutMs?: number },
): Promise<Record<string, unknown>> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options?.timeoutMs ?? DEFAULT_TIMEOUT);
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } finally {
    clearTimeout(timeout);
  }
}

export async function getJson(url: string, options?: { timeoutMs?: number }): Promise<Record<string, unknown>> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options?.timeoutMs ?? DEFAULT_TIMEOUT);
  try {
    const res = await fetch(url, { signal: controller.signal });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  } finally {
    clearTimeout(timeout);
  }
}

export async function postBinary(url: string, body: ArrayBuffer, options?: { timeoutMs?: number }): Promise<void> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options?.timeoutMs ?? DEFAULT_TIMEOUT);
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream" },
      body,
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(await res.text());
  } finally {
    clearTimeout(timeout);
  }
}

export { DEFAULT_LONG_TIMEOUT };
