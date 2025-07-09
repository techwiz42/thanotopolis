'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  isChunkError: boolean;
}

class ChunkErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    isChunkError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    // Check if this is a chunk loading error
    const isChunkError = error.message?.includes('Loading chunk') || 
                        error.message?.includes('ChunkLoadError') ||
                        error.name === 'ChunkLoadError';
    
    return { hasError: true, isChunkError };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Chunk loading error:', error, errorInfo);
    
    // If it's a chunk loading error, try to reload the page
    if (this.state.isChunkError) {
      console.log('Attempting to reload due to chunk loading error...');
      // Small delay to prevent infinite reload loops
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    }
  }

  public render() {
    if (this.state.hasError) {
      if (this.state.isChunkError) {
        return (
          <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-6">
              <div className="flex items-center space-x-2 mb-4">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Loading Update...
                </h2>
              </div>
              <p className="text-gray-600 mb-4">
                The application is loading updated content. This will only take a moment.
              </p>
              <button
                onClick={() => window.location.reload()}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
              >
                Reload Now
              </button>
            </div>
          </div>
        );
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Something went wrong
            </h2>
            <p className="text-gray-600 mb-4">
              An unexpected error occurred. Please try refreshing the page.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
            >
              Refresh Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ChunkErrorBoundary;