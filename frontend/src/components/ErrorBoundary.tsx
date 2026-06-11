import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

// Catches render-time errors anywhere in the subtree so a single failing component cannot
// blank the whole app — surfaces a recoverable message instead.
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // In production this would report to an error sink; we keep a console trace.
    console.error("UI error boundary caught:", error, info.componentStack);
  }

  handleReset = (): void => {
    this.setState({ hasError: false, message: "" });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="error" data-testid="error-boundary">
          Something went wrong rendering this view.
          <button className="btn btn--ghost" onClick={this.handleReset} data-testid="error-reset">
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
