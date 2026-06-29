import type { SourceRef } from "@/lib/types";
import { fmtDate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";

/**
 * Provenance is mandatory in a decision system: every fact must show where it
 * came from and when it was captured. M3.2 adds the minimal built-in provenance
 * (provider / dataset / raw snapshot locator / content hash) so a value like
 * "ROE 25%" can answer: which provider, which dataset, captured when, from which
 * raw snapshot.
 */
export function SourceTag({ source }: { source: SourceRef | null | undefined }) {
  if (!source) return <span className="text-muted-foreground">—</span>;
  const dataset = source.dataset ?? source.provider ?? source.source_id;
  return (
    <span
      className="inline-flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground"
      title={
        source.raw_snapshot_ref
          ? `raw: ${source.raw_snapshot_ref}${source.hash ? `\nhash: ${source.hash}` : ""}`
          : undefined
      }
    >
      <Badge variant="muted">{source.source_name}</Badge>
      {dataset ? <span className="font-mono">{dataset}</span> : null}
      <span className="font-mono">{source.trust_level}</span>
      <span>· {fmtDate(source.captured_at)}</span>
    </span>
  );
}

