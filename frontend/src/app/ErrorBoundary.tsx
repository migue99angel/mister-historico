import { Component, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  override state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  override render() {
    if (this.state.error) {
      return (
        <main className="flex min-h-dvh flex-col items-center justify-center gap-4 px-6 py-12 text-center">
          <h1 className="text-3xl font-bold">Se ha producido un error</h1>
          <p role="alert">{this.state.error.message}</p>
        </main>
      );
    }

    return this.props.children;
  }
}
