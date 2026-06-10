// Status: real
import { Component, type ErrorInfo, type ReactNode } from 'react';
import { ErrorState } from './StateView';

type Props = {
  children: ReactNode;
  resetKey?: string;
};

type State = {
  hasError: boolean;
};

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('资源渲染异常', error, info);
  }

  componentDidUpdate(prevProps: Props) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false });
    }
  }

  private reset = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      return (
        <ErrorState
          message="资源渲染异常，请刷新或切换其他资源"
          onRetry={this.reset}
          retryText="重置"
        />
      );
    }

    return this.props.children;
  }
}
