import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { getCompany } from "@/lib/api";
import {
  ANNOUNCEMENT_TYPE_LABEL,
  FACT_TYPE_LABEL,
  fmtDate,
  fmtNumber,
} from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Section, KeyValue, Empty } from "@/components/section";
import { SourceTag } from "@/components/source-tag";
import { CompanyTimelineView } from "@/components/company-timeline";
import { RecordRecent } from "@/components/record-recent";

export default async function CompanyDetailPage({
  params,
}: {
  params: Promise<{ tsCode: string }>;
}) {
  const { tsCode } = await params;
  const decoded = decodeURIComponent(tsCode);
  const data = await getCompany(decoded).catch(() => null);
  if (!data) notFound();

  const profileFacts = data.facts.filter((f) => f.fact_type === "profile");
  const otherFacts = data.facts.filter(
    (f) => f.fact_type !== "profile" && f.fact_type !== "quote",
  );

  return (
    <div className="space-y-8">
      <RecordRecent tsCode={data.security.ts_code} name={data.company.name} />
      <div className="space-y-2">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" /> 返回搜索
        </Link>
        <div className="flex items-baseline gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">
            {data.company.name}
          </h1>
          <code className="rounded bg-muted px-2 py-0.5 font-mono text-sm">
            {data.security.ts_code}
          </code>
        </div>
        <p className="text-sm text-muted-foreground">
          只读公司认知视图 · 数据模型验证（Console Alpha）
        </p>
      </div>

      {/* Identity: Company -> ListedEntity -> Security -> Listing */}
      <Section
        title="Identity"
        subtitle="Company → ListedEntity → Security → Listing（代理键身份，ts_code 仅为属性）"
      >
        <div className="rounded-lg border bg-card p-4">
          <KeyValue label="Company">
            <code className="font-mono text-xs">{data.company.company_id}</code>
            <span className="ml-2">{data.company.name}</span>
          </KeyValue>
          <KeyValue label="ListedEntity">
            <code className="font-mono text-xs">
              {data.listed_entity.listed_entity_id}
            </code>
            <span className="ml-2">{data.listed_entity.disclosure_name}</span>
          </KeyValue>
          <KeyValue label="Security">
            <code className="font-mono text-xs">
              {data.security.security_id}
            </code>
            <span className="ml-2">
              ts_code <code className="font-mono">{data.security.ts_code}</code>
            </span>
          </KeyValue>
          <KeyValue label="Listing">
            <code className="font-mono text-xs">{data.listing.listing_id}</code>
            <span className="ml-2">
              {data.listing.exchange} / {data.listing.board} ·{" "}
              <Badge variant="muted">{data.listing.status}</Badge>
            </span>
          </KeyValue>
          <KeyValue label="地区">{data.company.region ?? "—"}</KeyValue>
          <KeyValue label="外部标识">
            {data.company.external_ids.length
              ? data.company.external_ids.map((id) => (
                  <code
                    key={id}
                    className="mr-1.5 rounded bg-muted px-1.5 py-0.5 font-mono text-xs"
                  >
                    {id}
                  </code>
                ))
              : "—"}
          </KeyValue>
          {data.industry && (
            <KeyValue label="行业">
              {data.industry.name}{" "}
              <span className="text-xs text-muted-foreground">
                （{data.industry.taxonomy}）
              </span>
            </KeyValue>
          )}
          {data.latest_quote && (
            <KeyValue label="最新收盘">
              {fmtNumber(data.latest_quote.close)} ·{" "}
              <span className="text-xs text-muted-foreground">
                {fmtDate(data.latest_quote.trade_date)}
              </span>
            </KeyValue>
          )}
        </div>
      </Section>

      {/* Latest profile / generic facts */}
      <Section
        title="Facts"
        subtitle="MarketFact v1 · subject — predicate — object（资料 / 行业 / 政策类通用事实）"
      >
        {profileFacts.length + otherFacts.length === 0 ? (
          <Empty text="暂无通用事实" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">类型</TableHead>
                <TableHead>谓词 (predicate)</TableHead>
                <TableHead>取值 (object)</TableHead>
                <TableHead className="w-44">来源</TableHead>
                <TableHead className="w-16">置信度</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[...profileFacts, ...otherFacts].map((f) => (
                <TableRow key={f.fact_id}>
                  <TableCell>
                    <Badge>{FACT_TYPE_LABEL[f.fact_type] ?? f.fact_type}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs">
                    {f.predicate}
                  </TableCell>
                  <TableCell className="text-sm">{f.object_value}</TableCell>
                  <TableCell>
                    <SourceTag source={f.source_ref} />
                  </TableCell>
                  <TableCell className="text-xs">{f.confidence}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Section>

      {/* Financial timeline */}
      <Section
        title="Financial Facts"
        subtitle="FinancialFact · 结构化财务指标（需 fina_indicator 数据源）"
      >
        {data.financial_facts.length === 0 ? (
          <Empty text="暂无财务事实" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-24">报告期</TableHead>
                <TableHead>指标</TableHead>
                <TableHead>数值</TableHead>
                <TableHead className="w-20">同比</TableHead>
                <TableHead className="w-44">来源</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.financial_facts.map((f) => (
                <TableRow key={f.fact_id}>
                  <TableCell className="font-mono text-xs">
                    {f.report_period}
                  </TableCell>
                  <TableCell className="text-sm">{f.metric_name}</TableCell>
                  <TableCell className="text-sm">
                    {fmtNumber(f.metric_value)}{" "}
                    <span className="text-xs text-muted-foreground">
                      {f.unit}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs">
                    {f.yoy === null ? "—" : `${f.yoy}%`}
                  </TableCell>
                  <TableCell>
                    <SourceTag source={f.source_ref} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Section>

      {/* Announcement timeline */}
      <Section
        title="Announcements"
        subtitle="AnnouncementFact · 公司公告（需 anns_d 数据源）"
      >
        {data.announcement_facts.length === 0 ? (
          <Empty text="暂无公告事实" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-28">披露日期</TableHead>
                <TableHead className="w-28">类型</TableHead>
                <TableHead>标题</TableHead>
                <TableHead className="w-20">原文</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.announcement_facts.map((f) => (
                <TableRow key={f.fact_id}>
                  <TableCell className="font-mono text-xs">
                    {fmtDate(f.published_at)}
                  </TableCell>
                  <TableCell>
                    <Badge>
                      {ANNOUNCEMENT_TYPE_LABEL[f.announcement_type] ??
                        f.announcement_type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm">{f.title || "—"}</TableCell>
                  <TableCell>
                    {f.document_url ? (
                      <a
                        href={f.document_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-ring hover:underline"
                      >
                        原文 <ExternalLink className="size-3" />
                      </a>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Section>

      {/* Unified timeline (read model) */}
      <Section
        title="Timeline"
        subtitle="统一公司知识时间线（read model）：通用 / 财务 / 公告事实投影到一条时间线，三时间戳永不塌缩"
      >
        <CompanyTimelineView tsCode={decoded} initialEvents={data.timeline} />
      </Section>

      {/* Sources */}
      <Section title="Sources" subtitle="本视图所依据的数据来源">
        {data.source_refs.length === 0 ? (
          <Empty text="无来源记录" />
        ) : (
          <div className="flex flex-wrap gap-2">
            {data.source_refs.map((s, i) => (
              <SourceTag key={`${s.source_id}-${i}`} source={s} />
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}
