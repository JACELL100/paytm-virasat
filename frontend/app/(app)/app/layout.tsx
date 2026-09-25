import { AppShell } from "@/components/layout/app-shell";

export default function OwnerAppLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
