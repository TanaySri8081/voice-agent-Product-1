import React from "react";

// Catches render-time errors anywhere below it and shows the message instead of
// a blank white screen. Helps diagnose crashes in development and gives users a
// recoverable state in production.
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Surfaced in the browser console for debugging.
    console.error("App crashed:", error, info?.componentStack);
  }

  render() {
    if (this.state.error) {
      const e = this.state.error;
      return (
        <div style={{ padding: 24, fontFamily: "ui-monospace, monospace", color: "#111827" }}>
          <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: 12 }}>Something went wrong.</h1>
          <p style={{ marginBottom: 12, color: "#6b7280" }}>
            An error stopped the page from loading. Try reloading. If it persists, share the message below.
          </p>
          <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", color: "#b91c1c", background: "#fef2f2", padding: 16, borderRadius: 12 }}>
            {String(e?.stack || e?.message || e)}
          </pre>
          <button
            onClick={() => { this.setState({ error: null }); window.location.reload(); }}
            style={{ marginTop: 16, padding: "8px 16px", borderRadius: 10, background: "#111827", color: "#fff", border: 0, cursor: "pointer" }}
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
