import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { BookCard } from '../ui/BookCard';
import { BookButton } from '../ui/BookButton';

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

/**
 * 页面级错误边界：避免单个组件异常导致整站白屏。
 *
 * 说明：仅用于兜底渲染错误，不替代接口错误处理。
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('WebUI 渲染异常（ErrorBoundary 捕获）:', error, errorInfo);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="min-h-[60vh] flex items-center justify-center p-6">
        <BookCard className="max-w-xl w-full p-6">
          <div className="flex items-center gap-3 text-book-text-main">
            <AlertTriangle className="text-book-accent" size={22} />
            <div className="font-serif text-lg font-bold">页面渲染出错</div>
          </div>

          <div className="mt-3 text-sm text-book-text-muted leading-relaxed">
            这通常是某个组件的状态/数据不符合预期导致的。你可以尝试刷新页面继续使用。
          </div>

          {this.state.error?.message && (
            <pre className="mt-4 p-3 text-xs bg-book-bg rounded-lg border border-book-border/40 overflow-auto text-book-text-tertiary">
              {this.state.error.message}
            </pre>
          )}

          <div className="mt-5 flex justify-end gap-2">
            <BookButton
              variant="ghost"
              onClick={() => this.setState({ hasError: false, error: undefined })}
            >
              返回
            </BookButton>
            <BookButton
              variant="primary"
              onClick={() => window.location.reload()}
            >
              <RefreshCw size={16} className="mr-2" />
              刷新
            </BookButton>
          </div>
        </BookCard>
      </div>
    );
  }
}
