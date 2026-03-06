import React, { useEffect, useRef } from 'react';
import { annotate } from 'rough-notation';
import type { RoughAnnotationType } from 'rough-notation/lib/model';

interface HighlighterProps {
  children: React.ReactNode;
  color?: string;
  action?: RoughAnnotationType;
  strokeWidth?: number;
  animationDuration?: number;
  iterations?: number;
  padding?: number;
  multiline?: boolean;
  delay?: number;
}

export const Highlighter: React.FC<HighlighterProps> = ({
  children,
  color = '#ffd1dc',
  action = 'highlight',
  strokeWidth = 1.5,
  animationDuration = 500,
  iterations = 2,
  padding = 2,
  multiline = true,
  delay = 0,
}) => {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!ref.current) return;

    const annotation = annotate(ref.current, {
      type: action,
      color,
      strokeWidth,
      animationDuration,
      iterations,
      padding,
      multiline,
    });

    const timer = setTimeout(() => {
      annotation.show();
    }, delay);

    return () => {
      clearTimeout(timer);
      annotation.remove();
    };
  }, [action, color, strokeWidth, animationDuration, iterations, padding, multiline, delay]);

  return <span ref={ref}>{children}</span>;
};
