"use client";

import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";

export function LogoutButton() {
  const router = useRouter();

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <button
      onClick={handleLogout}
      className="text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1 text-sm"
      title="Sign out"
    >
      <LogOut className="h-4 w-4" />
    </button>
  );
}
