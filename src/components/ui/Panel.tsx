import type { ReactNode } from "react";

interface PanelProps {
  children: ReactNode;
  className?: string;
  noPadding?: boolean;
}

/**
 * Base panel/card container. Deliberately restrained: hairline border,
 * near-flat surface, no drop shadows or rounded-pill corners, to read as
 * instrumentation rather than a generic SaaS card.
 */
export function Panel({ children, className = "", noPadding = false }: PanelProps) {
  return (
    <div
      className={`relative bg-panel border border-line rounded-sm ${
        noPadding ? "" : "p-4"
      } ${className}`}
    >
      {children}
    </div>
  );
}

interface PanelHeaderProps {
  title: string;
  eyebrow?: string;
  right?: ReactNode;
}

export function PanelHeader({ title, eyebrow, right }: PanelHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-3 pb-3 border-b border-line">
      <div>
        {eyebrow && (
          <div className="text-[10px] tracking-[0.18em] text-tertiary font-data mb-0.5 uppercase">
            {eyebrow}
          </div>
        )}
        <h2 className="font-display text-[13px] font-semibold tracking-[0.08em] text-primary uppercase">
          {title}
        </h2>
      </div>
      {right && <div>{right}</div>}
    </div>
  );
}
