import React from "react";

interface Props {
  children: React.ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          padding: 40,
          color: "#edf0f7",
          textAlign: "center",
          gap: 16,
        }}>
          <div style={{ fontSize: 48, fontWeight: 700, opacity: 0.3 }}>G</div>
          <h2 style={{ fontSize: 18, fontWeight: 600 }}>Something went wrong</h2>
          <p style={{ color: "#8e99ae", fontSize: 13, maxWidth: 400 }}>
            {this.state.error.message}
          </p>
          <button
            onClick={() => { this.setState({ error: null }); window.location.reload(); }}
            style={{
              padding: "8px 16px",
              borderRadius: 12,
              border: "1px solid rgba(255,255,255,0.1)",
              background: "#3b7dff",
              color: "#fff",
              fontSize: 13,
              fontWeight: 550,
              cursor: "pointer",
            }}
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
