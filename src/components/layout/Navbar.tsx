import Link from "next/link";
import { Calendar, FileText, Search, Settings } from "lucide-react";
import { getSession } from "@/lib/auth";
import { LogoutButton } from "./LogoutButton";

export async function Navbar() {
  const session = await getSession();

  return (
    <header className="border-b bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/" className="flex items-center gap-2">
          <FileText className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold tracking-tight">FOIA</span>
          <span className="hidden text-sm text-muted-foreground sm:inline">
            Michigan Public Records
          </span>
        </Link>
        <nav className="flex items-center gap-6 text-sm">
          <Link
            href="/browse"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Browse
          </Link>
          <Link
            href="/calendar"
            className="text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
          >
            <Calendar className="h-4 w-4" />
            Calendar
          </Link>
          <Link
            href="/search"
            className="text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
          >
            <Search className="h-4 w-4" />
            Search
          </Link>
          <Link
            href="/about"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            About
          </Link>
          {session && (
            <>
              <Link
                href="/settings/staff"
                className="text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
              >
                <Settings className="h-4 w-4" />
                Settings
              </Link>
              <LogoutButton />
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
