import type { ReactNode } from "react";

import ProviderShell from "@/components/provider/provider-shell";

export default function ProviderLayout({ children }: { children: ReactNode }) {
  return <ProviderShell>{children}</ProviderShell>;
}
