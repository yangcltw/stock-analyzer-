import { StockResponse } from "@/types/stock";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchStock(symbol: string): Promise<StockResponse> {
  const res = await fetch(`${API_URL}/api/stock/${symbol}`);
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Connect to AI analysis SSE stream.
 * Returns an AbortController for cleanup.
 *
 * @param symbol - Stock symbol
 * @param onToken - Called for each streaming token
 * @param onDone - Called when streaming completes with full text
 * @param onError - Called on error
 */
export function streamAIAnalysis(
  symbol: string,
  onToken: (text: string) => void,
  onDone: (fullText: string) => void,
  onError: (message: string) => void,
): AbortController {
  const controller = new AbortController();

  const connect = async () => {
    try {
      const res = await fetch(`${API_URL}/api/stock/${symbol}/ai`, {
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        onError("AI analysis unavailable");
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let eventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const raw = line.slice(6);
            try {
              const data = JSON.parse(raw);
              switch (eventType) {
                case "token":
                  onToken(data.text);
                  break;
                case "done":
                case "cached":
                  onDone(data.text);
                  break;
                case "error":
                  onError(data.message);
                  break;
              }
            } catch {
              // skip malformed JSON
            }
            eventType = "";
          }
        }
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        // Expected — user navigated away or new search
        return;
      }
      onError("AI connection lost");
    }
  };

  connect();
  return controller;
}
