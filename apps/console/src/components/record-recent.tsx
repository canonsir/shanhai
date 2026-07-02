"use client";

import * as React from "react";
import { recordRecentCompany } from "@/lib/recent";

/**
 * Records a company visit into the localStorage-backed recent list.
 * Rendered (invisibly) by the server detail page so the sidebar history
 * rail updates as the user browses.
 */
export function RecordRecent({
  tsCode,
  name,
}: {
  tsCode: string;
  name: string;
}) {
  React.useEffect(() => {
    recordRecentCompany({ tsCode, name });
  }, [tsCode, name]);

  return null;
}
