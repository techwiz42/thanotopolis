// Client-side chunk error handler
export const setupChunkErrorHandler = () => {
  // Only run on client side
  if (typeof window === 'undefined') return;

  // Handle unhandled promise rejections (chunk loading errors)
  window.addEventListener('unhandledrejection', (event) => {
    const error = event.reason;
    
    // Check if this is a chunk loading error
    if (
      error instanceof Error &&
      (error.message?.includes('Loading chunk') ||
       error.message?.includes('ChunkLoadError') ||
       error.name === 'ChunkLoadError')
    ) {
      console.warn('Chunk loading error detected, attempting recovery...');
      
      // Prevent the default error handling
      event.preventDefault();
      
      // Try to reload the page after a short delay
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    }
  });

  // Handle script loading errors
  window.addEventListener('error', (event) => {
    const { target } = event;
    
    // Check if this is a script loading error
    if (
      target instanceof HTMLScriptElement &&
      target.src?.includes('_next/static/chunks/')
    ) {
      console.warn('Script chunk loading error detected:', target.src);
      
      // Try to reload the page after a short delay
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    }
  });
};

// Initialize the error handler
setupChunkErrorHandler();