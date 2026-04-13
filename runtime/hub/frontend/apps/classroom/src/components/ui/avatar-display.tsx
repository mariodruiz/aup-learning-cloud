
import { cn } from '@/lib/utils';
import { resolveStaticPath } from '@/lib/asset-path';

interface AvatarDisplayProps {
  readonly src: string;
  readonly alt?: string;
  readonly className?: string;
}

export function AvatarDisplay({ src, alt, className }: AvatarDisplayProps) {
  const resolved = resolveStaticPath(src) || src;
  const isUrl = resolved.startsWith('http') || resolved.startsWith('data:') || resolved.startsWith('/');

  if (isUrl) {
    return (
      <img src={resolved} alt={alt || ''} className={cn('w-full h-full object-cover', className)} />
    );
  }

  return (
    <span
      role="img"
      aria-label={alt || ''}
      className={cn('flex items-center justify-center w-full h-full select-none', className)}
    >
      {src}
    </span>
  );
}
