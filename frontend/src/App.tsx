import { useEffect, useMemo, useRef, useState } from "react";

/** WebSocket event protocol — mirror of backend/agent/events.py */
type Finding = {
  tooth_region?: string;
  label?: string;
  confidence?: number;
  bbox?: number[]; // [x, y, w, h] in the 240x170 radiograph space
};
type Evt = {
  type: string;
  text?: string;
  tool?: string;
  args?: Record<string, unknown>;
  summary?: string;
  kind?: string;
  content?: string;
  disclaimer?: string;
  message?: string;
  findings?: Finding[];
  low_confidence?: Finding[];
};

const WS_URL = (import.meta as any).env?.VITE_WS_URL ?? "ws://localhost:8000/ws";
const API = WS_URL.replace(/^ws/, "http").replace(/\/ws$/, "");

const DRAFT_META: Record<string, { icon: string; label: string }> = {
  patient_summary: { icon: "ti-user-heart", label: "Patient summary" },
  treatment_plan: { icon: "ti-clipboard-list", label: "Treatment plan" },
  insurance_narrative: { icon: "ti-shield-half", label: "Insurance pre-auth" },
};

const INFO = "var(--color-text-info)";
const OK = "var(--color-text-success)";
const WARN = "var(--color-text-warning)";
const DANGER = "var(--color-text-danger)";
const MUTE = "var(--color-text-tertiary)";

/** "dentist_flag" -> "Dentist flag" */
function titleCase(s: string): string {
  return s.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Render a proposed-action object as a readable sentence (shapes vary by model). */
function formatAction(a: any): string {
  if (a == null || typeof a !== "object") return String(a);
  const type = typeof a.type === "string" ? titleCase(a.type) : "Action";
  const tooth = a.tooth_region || a.tooth || a.region;
  const interval = a.interval_months ?? a.interval ?? a.months;
  const detail = a.reason || a.note || a.description || a.message || "";
  const head = [type, tooth ? `(${tooth})` : "", interval != null ? `· ${typeof interval === "number" ? `${interval}-month` : interval}` : ""]
    .filter(Boolean)
    .join(" ");
  return detail ? `${head} — ${detail}` : head;
}

/** Per-event icon + colour for the live timeline. */
function rowStyle(e: Evt): { icon: string; color: string } {
  switch (e.type) {
    case "agent_step":
      return { icon: "ti-bulb", color: INFO };
    case "tool_call":
      return { icon: "ti-tool", color: "var(--color-text-secondary)" };
    case "tool_result":
      return { icon: "ti-check", color: OK };
    case "flag":
      return { icon: "ti-flag", color: WARN };
    case "final":
      return { icon: "ti-circle-check", color: OK };
    case "error":
      return { icon: "ti-alert-triangle", color: DANGER };
    default:
      return { icon: "ti-point", color: MUTE };
  }
}

function Icon({ name, color }: { name: string; color?: string }) {
  return <i className={`ti ${name}`} style={color ? { color } : undefined} aria-hidden="true" />;
}

export default function App() {
  const [events, setEvents] = useState<Evt[]>([]);
  const [drafts, setDrafts] = useState<Record<string, Evt>>({});
  const [findings, setFindings] = useState<Finding[]>([]);
  const [lowConf, setLowConf] = useState<Finding[]>([]);
  const [actions, setActions] = useState<unknown[] | null>(null);
  const [flags, setFlags] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const [running, setRunning] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const timelineRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let closed = false;
    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        if (!closed) setTimeout(connect, 1500); // auto-reconnect
      };
      ws.onmessage = (m) => {
        const e: Evt = JSON.parse(m.data);
        setEvents((prev) => [...prev, e]);
        if (e.type === "draft" && e.kind) {
          setDrafts((d) => ({ ...d, [e.kind as string]: e }));
        }
        if (e.type === "tool_result" && e.tool === "read_radiograph") {
          setFindings(e.findings ?? []);
          setLowConf(e.low_confidence ?? []);
        }
        if (e.type === "tool_call" && e.tool === "propose_actions") {
          const a = (e.args as any)?.actions;
          if (Array.isArray(a)) setActions(a);
        }
        if (e.type === "flag" && e.text) setFlags((f) => [...f, e.text as string]);
        if (e.type === "final" || e.type === "error") setRunning(false);
      };
    }
    connect();
    return () => {
      closed = true;
      wsRef.current?.close();
    };
  }, []);

  // keep the timeline scrolled to the newest event
  useEffect(() => {
    const el = timelineRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events]);

  const run = async () => {
    setEvents([]);
    setDrafts({});
    setFindings([]);
    setLowConf([]);
    setActions(null);
    setFlags([]);
    setRunning(true);
    try {
      await fetch(`${API}/demo`, { method: "POST" });
    } catch {
      setRunning(false);
    }
  };

  const overlays = useMemo(
    () =>
      [
        ...findings.map((f) => ({ f, low: false })),
        ...lowConf.map((f) => ({ f, low: true })),
      ].filter((o) => Array.isArray(o.f.bbox) && o.f.bbox!.length === 4),
    [findings, lowConf]
  );

  const hasActions = (actions && actions.length > 0) || flags.length > 0;

  return (
    <div className="wrap">
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1>DentOps Copilot</h1>
          <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
            Agentic dental copilot · drafts for dentist review
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={run} disabled={running} style={{ color: INFO, borderColor: "var(--color-border-info)" }}>
            <Icon name={running ? "ti-loader-2" : "ti-player-play"} /> Run demo · patient #1042
          </button>
        </div>
      </div>

      {/* Status chips */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 12 }}>
        <span className="dc-chip"><Icon name="ti-server-2" /> FastMCP server: dentops</span>
        <span className="dc-chip"><Icon name="ti-tool" /> 5 tools</span>
        <span className="dc-chip"><Icon name="ti-files" /> resources</span>
        <span className="dc-chip"><Icon name="ti-message-2" /> prompts</span>
        <span className="dc-chip">
          <Icon name="ti-plug-connected" color={connected ? OK : DANGER} />
          WebSocket {connected ? "connected" : "disconnected"}
        </span>
      </div>

      {/* Stage: radiograph + timeline */}
      <div className="stage">
        <div className="dc-card" style={{ padding: "0.8rem" }}>
          <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 8 }}>Radiograph</div>
          <svg viewBox="0 0 240 170" width="100%" role="img" aria-label="Illustrative bitewing radiograph with highlighted finding regions">
            <rect x="0" y="0" width="240" height="170" rx="8" fill="#1d2433" />
            <g fill="#ccd2de">
              {[16, 52, 88, 124, 160, 196].map((x) => (
                <rect key={`t${x}`} x={x} y={30} width={28} height={52} rx={6} />
              ))}
              {[16, 52, 88, 124, 160, 196].map((x) => (
                <rect key={`b${x}`} x={x} y={92} width={28} height={52} rx={6} />
              ))}
            </g>
            {overlays.map(({ f, low }, i) => {
              const [x, y, w, h] = f.bbox as number[];
              return (
                <rect
                  key={`f${i}`}
                  x={x}
                  y={y}
                  width={w}
                  height={h}
                  rx={3}
                  fill="none"
                  stroke={low ? "var(--finding-low)" : "var(--finding-high)"}
                  strokeWidth={2}
                  strokeDasharray={low ? "4 3" : undefined}
                />
              );
            })}
          </svg>
          <div style={{ fontSize: 11, color: MUTE, marginTop: 6 }}>
            Illustrative placeholder — detector is third-party / mock.
          </div>
          <div style={{ fontSize: 12, marginTop: 10, lineHeight: 1.9 }}>
            {findings.length === 0 && lowConf.length === 0 ? (
              <span className="dc-muted">Run the demo to populate findings.</span>
            ) : (
              <>
                {findings.map((f, i) => (
                  <div key={`hf${i}`}>
                    <span className="dc-dot" style={{ background: "var(--finding-high)" }} />
                    {f.tooth_region} · {f.label} · conf {f.confidence}
                  </div>
                ))}
                {lowConf.map((f, i) => (
                  <div key={`lf${i}`}>
                    <span className="dc-dot" style={{ background: "var(--finding-low)" }} />
                    {f.tooth_region} · {f.label} · conf {f.confidence} · flagged
                  </div>
                ))}
              </>
            )}
          </div>
        </div>

        <div className="dc-card">
          <div style={{ fontSize: 13, fontWeight: 500 }}>Live agent timeline</div>
          <div style={{ fontSize: 12, color: "var(--color-text-secondary)", marginBottom: 4 }}>
            Streamed over WebSocket as the agent calls MCP tools
          </div>
          <div className="timeline" ref={timelineRef}>
            {events.filter((e) => e.type !== "draft").length === 0 ? (
              <div className="dc-ev">
                <Icon name="ti-player-play" color={MUTE} />
                <div className="dc-muted">Idle — press run to start.</div>
              </div>
            ) : (
              events
                .filter((e) => e.type !== "draft")
                .map((e, i) => {
                  const { icon, color } = rowStyle(e);
                  return (
                    <div className="dc-ev" key={i}>
                      <Icon name={icon} color={color} />
                      <div>
                        {e.type === "tool_call" ? (
                          <>
                            <span className="dc-lab">calls</span>{" "}
                            <span className="dc-mono">{e.tool}</span>
                            {e.args ? <div className="dc-mono">{JSON.stringify(e.args)}</div> : null}
                          </>
                        ) : e.type === "tool_result" ? (
                          <>
                            returns <span className="dc-mono">{e.summary}</span>
                          </>
                        ) : (
                          <span>{e.text || e.message || e.summary}</span>
                        )}
                      </div>
                    </div>
                  );
                })
            )}
          </div>
        </div>
      </div>

      {/* Drafts */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "1.1rem 0 0.6rem" }}>
        <span style={{ fontSize: 13, fontWeight: 500 }}>Drafts</span>
        <span className="dc-ban">draft — for dentist review</span>
      </div>
      <div className="drafts">
        {Object.entries(DRAFT_META).map(([kind, meta]) => {
          const d = drafts[kind];
          return (
            <div className="dc-card" key={kind}>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 6 }}>
                <Icon name={meta.icon} /> {meta.label}
              </div>
              {d ? (
                <div style={{ fontSize: 13, lineHeight: 1.6 }}>
                  <div className="dc-ban" style={{ marginBottom: 6 }}>
                    {d.disclaimer ?? "draft — for dentist review"}
                  </div>
                  {d.content}
                </div>
              ) : (
                <div className="dc-muted" style={{ fontSize: 13 }}>Not run yet.</div>
              )}
            </div>
          );
        })}

        {/* Proposed actions card (from flag + propose_actions events) */}
        <div className="dc-card">
          <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 6 }}>
            <Icon name="ti-checkup-list" /> Proposed actions
          </div>
          {hasActions ? (
            <div style={{ fontSize: 13, lineHeight: 1.6 }}>
              <div className="dc-ban" style={{ marginBottom: 6 }}>draft — for dentist review</div>
              {actions && actions.length > 0
                ? actions.map((a, i) => (
                    <div key={`ac${i}`} style={{ marginBottom: 4 }}>• {formatAction(a)}</div>
                  ))
                : flags.map((t, i) => (
                    <div key={`fl${i}`} style={{ marginBottom: 4 }}>• {t}</div>
                  ))}
              <div className="dc-muted" style={{ fontSize: 12, marginTop: 4 }}>
                Nothing is sent automatically.
              </div>
            </div>
          ) : (
            <div className="dc-muted" style={{ fontSize: 13 }}>Not run yet.</div>
          )}
        </div>
      </div>

      <div style={{ fontSize: 11, color: MUTE, marginTop: "1rem", lineHeight: 1.6 }}>
        Patient data and detector output are mock fixtures. Not a medical device; every output is a
        draft for dentist review.
      </div>
    </div>
  );
}
