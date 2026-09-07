type Tone = "cyan" | "amber" | "red" | "green" | "blue" | "neutral";

const DOT_COLOR: Record<Tone, string> = {
  cyan: "bg-cyan",
  amber: "bg-amber",
  red: "bg-red",
  green: "bg-green",
  blue: "bg-blue",
  neutral: "bg-tertiary",
};

const TEXT_COLOR: Record<Tone, string> = {
  cyan: "text-cyan",
  amber: "text-amber",
  red: "text-red",
  green: "text-green",
  blue: "text-blue",
  neutral: "text-tertiary",
};

interface StatusDotProps {
  tone: Tone;
  pulse?: boolean;
  size?: "sm" | "md";
}

/** A single glowing status dot, e.g. for "ONLINE" indicators. */
export function StatusDot({ tone, pulse = false, size = "sm" }: StatusDotProps) {
  const dim = size === "sm" ? "w-1.5 h-1.5" : "w-2 h-2";
  return (
    <span
      className={`inline-block rounded-full ${dim} ${DOT_COLOR[tone]} ${
        pulse ? "animate-pulse-dot" : ""
      }`}
    />
  );
}

interface StatusBadgeProps {
  label: string;
  tone: Tone;
  pulse?: boolean;
}

/** Dot + uppercase label pair, used for compact status readouts. */
export function StatusBadge({ label, tone, pulse = false }: StatusBadgeProps) {
  return (
    <div className="flex items-center gap-1.5">
      <StatusDot tone={tone} pulse={pulse} />
      <span className={`font-data text-[11px] tracking-[0.06em] uppercase ${TEXT_COLOR[tone]}`}>
        {label}
      </span>
    </div>
  );
}

export type { Tone };
