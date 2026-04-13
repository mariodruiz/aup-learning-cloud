import '@fontsource-variable/inter';
import 'katex/dist/katex.min.css';
import './styles/globals.css';

import { ThemeProvider } from '@/lib/hooks/use-theme';
import { I18nProvider } from '@/lib/hooks/use-i18n';
import { Toaster } from '@/components/ui/sonner';
import { ServerProvidersInit } from '@/components/server-providers-init';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <I18nProvider>
        <ServerProvidersInit />
        {children}
        <Toaster position="top-center" />
      </I18nProvider>
    </ThemeProvider>
  );
}
