// A crash in one part of the screen shows a message there, never a blank page.

import { Component, type ErrorInfo, type ReactNode } from "react";
import { RotateCw } from "./icons";
import { Button, Msg } from "./ui";

/** Catches a render error below it and shows what broke, with Try again. `resetKey` clears the
 *  error when it changes (for example, when the reviewer opens another run). */
export class Boundary extends Component<{ children: ReactNode; what: string; resetKey?: unknown },
  { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) { return { error }; }

  componentDidCatch(error: Error, info: ErrorInfo) { console.error(error, info.componentStack); }

  componentDidUpdate(prev: { resetKey?: unknown }) {
    if (this.state.error && prev.resetKey !== this.props.resetKey) this.setState({ error: null });
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="stack">
        <Msg tone="bad">
          <b>{this.props.what} could not be shown.</b> The screen hit an error: {this.state.error.message}
        </Msg>
        <div><Button icon={RotateCw} onClick={() => this.setState({ error: null })}>Try again</Button></div>
      </div>
    );
  }
}
