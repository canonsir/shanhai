import type { SourceRef } from "@/lib/types";
import { fmtDate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";

/**
 * Provenance is mandatory in a decision system: every fact must show where it
 * came from and when it was captured. (Richer provenance — dataset / raw_ref —
 * is registered for M3.2, not M3.1.)
 */
export function SourceTag({ source }: { source: SourceRef | null | undefined }) {
  if (!source) return <span className="text-muted-foreground">—</span>;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      <Badge variant="muted">{source.source_name}</Badge>
      <span className="font-mono">{source.trust_level}</span>
      <span>· {fmtDate(source.captured_at)}</span>
    </span>
  );
}
