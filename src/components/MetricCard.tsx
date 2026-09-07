interface MetricCardProps {
  label: string;
  value: string;
  unit?: string;
  tone?: "cyan" | "amber" | "green" | "primary";
}

const TONE_TEXT: Record<NonNullable<MetricCardProps["tone"]>, string> = {
  cyan: "text-cyan",
  amber: "text-amber",
  green: "text-green",
  primary: "text-primary",
};

export function MetricCard({ label, value, unit, tone = "primary" }: MetricCardProps) {
  return (
    <div className="bg-panel-inset border border-line rounded-sm px-3 py-2.5">
      <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase mb-1">
        {label}
      </div>
      <div className="flex items-baseline gap-1">
        <span className={`font-data text-[19px] leading-none ${TONE_TEXT[tone]}`}>{value}</span>
        {unit && <span className="font-data text-[11px] text-tertiary">{unit}</span>}
      </div>
    </div>
  );
}
