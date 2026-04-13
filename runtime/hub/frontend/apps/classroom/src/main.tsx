import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { installFetchProxy } from './lib/fetch-proxy';
import { Providers } from './providers';
import { AppErrorBoundary } from './error-boundary';
import { router } from './routes';

installFetchProxy();

const rootElement = document.getElementById('root');

if (rootElement) {
  createRoot(rootElement).render(
    <StrictMode>
      <AppErrorBoundary>
        <Providers>
          <RouterProvider router={router} />
        </Providers>
      </AppErrorBoundary>
    </StrictMode>,
  );
} else {
  console.error('Could not find root element');
}
