import { Suspense } from "react";
import { CompanySearch } from "@/components/company-search";

export default function HomePage() {
  return (
    <Suspense fallback={null}>
      <CompanySearch />
    </Suspense>
  );
}
