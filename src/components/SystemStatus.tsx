import { Panel, PanelHeader } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { SystemComponentStatus, SystemStatusItem } from "@/types/overwatch";

interface SystemStatusProps {
  items: SystemStatusItem[];
}

const TONE_BY_STATUS: Record<SystemComponentStatus, "green" | "cyan" | "amber" | "red" | "neutral"> = {
  ready: "green",
  active: "cyan",
  simulated: "amber",
  offline: "neutral",
  error: "red",
};

export function SystemStatus({ items }: SystemStatusProps) {
  return (
    <Panel>
      <PanelHeader title="System Status" eyebrow="Component Readiness" />
      <div className="space-y-2.5">
        {items.map((item) => (
          <div key={item.label} className="flex items-center justify-between">
            <span className="text-[12.5px] text-secondary">{item.label}</span>
            <StatusBadge
              label={item.status}
              tone={TONE_BY_STATUS[item.status]}
              pulse={item.status === "active"}
            />
          </div>
        ))}
      </div>
    </Panel>
  );
}
