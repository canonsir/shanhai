import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "ShanHai Console — Company Intelligence",
  description:
    "Knowledge model validator for ShanHai: company identity, facts, financials, announcements and timeline.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <header className="border-b bg-card">
          <div className="mx-auto max-w-5xl px-6 py-3 flex items-center justify-between">
            <Link href="/" className="font-semibold tracking-tight">
              ShanHai <span className="text-muted-foreground">Console</span>
            </Link>
            <span className="text-xs text-muted-foreground">
              Knowledge Model Validator · M3.1 Alpha
            </span>
          </div>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-8">
          {children}
        </main>
        <footer className="border-t bg-card">
          <div className="mx-auto max-w-5xl px-6 py-3 text-xs text-muted-foreground">
            页面不是展示数据，而是验证知识模型。若某区块无法自然表达，即说明模型需要修正。
          </div>
        </footer>
      </body>
    </html>
  );
}
