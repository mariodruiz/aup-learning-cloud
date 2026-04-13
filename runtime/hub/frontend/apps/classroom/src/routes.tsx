import { createHashRouter } from 'react-router-dom';
import { lazy, Suspense } from 'react';

const HomePage = lazy(() => import('./pages/home'));
const GenerationPreview = lazy(() => import('./pages/generation-preview'));
const Classroom = lazy(() => import('./pages/classroom'));

function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-muted-foreground">
      <div className="flex items-center gap-2">
        <div className="size-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
        <span className="text-sm">Loading...</span>
      </div>
    </div>
  );
}

function SuspenseWrapper({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<Loading />}>{children}</Suspense>;
}

export const router = createHashRouter([
  {
    path: '/',
    element: <SuspenseWrapper><HomePage /></SuspenseWrapper>,
  },
  {
    path: '/generation-preview',
    element: <SuspenseWrapper><GenerationPreview /></SuspenseWrapper>,
  },
  {
    path: '/classroom/:id',
    element: <SuspenseWrapper><Classroom /></SuspenseWrapper>,
  },
]);
