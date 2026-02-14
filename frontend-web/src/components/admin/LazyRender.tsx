import React, { useEffect, useRef, useState } from 'react';

interface LazyRenderProps {
  children: React.ReactNode;
  placeholderHeight?: number | string;
  rootMargin?: string;
  once?: boolean;
  className?: string;
}

export const LazyRender: React.FC<LazyRenderProps> = ({
  children,
  placeholderHeight = 240,
  rootMargin = '320px 0px',
  once = true,
  className,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const target = containerRef.current;
    if (!target) return;

    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (!entry) return;

        if (once) {
          if (entry.isIntersecting) {
            setIsVisible(true);
            observer.disconnect();
          }
          return;
        }

        setIsVisible(entry.isIntersecting);
      },
      {
        root: null,
        rootMargin,
        threshold: 0.01,
      }
    );

    observer.observe(target);

    return () => {
      observer.disconnect();
    };
  }, [once, rootMargin]);

  const minHeight = typeof placeholderHeight === 'number' ? `${placeholderHeight}px` : placeholderHeight;

  return (
    <div ref={containerRef} className={className}>
      {isVisible ? (
        children
      ) : (
        <div
          className="w-full rounded-lg border border-book-border/30 bg-book-bg/50 animate-pulse"
          style={{ minHeight }}
          aria-hidden="true"
        />
      )}
    </div>
  );
};
