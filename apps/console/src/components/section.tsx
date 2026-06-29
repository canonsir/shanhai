import * as React from "react";
import { Separator } from "@/components/ui/separator";

export function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-base font-semibold tracking-tight">{title}</h2>
        {subtitle && (
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        )}
      </div>
      <Separator />
      {children}
    </section>
  );
}

export function KeyValue({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[140px_1fr] gap-3 py-1.5 text-sm">
      <div className="text-muted-foreground">{label}</div>
      <div>{children}</div>
    </div>
  );
}

export function Empty({ text }: { text: string }) {
  return <p className="text-sm italic text-muted-foreground">{text}</p>;
}
