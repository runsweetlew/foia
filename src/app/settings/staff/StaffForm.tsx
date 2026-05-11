"use client";

import { useState } from "react";

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  isActive: boolean;
  lastLoginAt: string | null;
  createdAt: string;
}

interface Props {
  user: User | null;
  onSaved: (user: User) => void;
  onCancel: () => void;
}

export function StaffForm({ user, onSaved, onCancel }: Props) {
  const isEdit = !!user;
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState(user?.role || "VIEWER");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);

    try {
      const body: Record<string, string> = { name, email, role };
      if (password) body.password = password;
      if (!isEdit && !password) {
        setError("Password is required for new users");
        setSaving(false);
        return;
      }

      const url = isEdit
        ? `/api/settings/staff/${user.id}`
        : "/api/settings/staff";
      const method = isEdit ? "PUT" : "POST";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Failed to save");
        return;
      }

      onSaved(data.user);
    } catch {
      setError("Network error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 max-w-md">
      {error && (
        <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 border border-red-200">
          {error}
        </div>
      )}

      <div>
        <label htmlFor="staff-name" className="block text-sm font-medium mb-1">
          Name
        </label>
        <input
          id="staff-name"
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>

      <div>
        <label htmlFor="staff-email" className="block text-sm font-medium mb-1">
          Email
        </label>
        <input
          id="staff-email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>

      <div>
        <label
          htmlFor="staff-password"
          className="block text-sm font-medium mb-1"
        >
          {isEdit ? "New Password (leave blank to keep current)" : "Password"}
        </label>
        <input
          id="staff-password"
          type="password"
          required={!isEdit}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          placeholder={isEdit ? "Leave blank to keep current" : "Min 8 characters"}
          minLength={isEdit && !password ? 0 : 8}
        />
      </div>

      <div>
        <label htmlFor="staff-role" className="block text-sm font-medium mb-1">
          Role
        </label>
        <select
          id="staff-role"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="ADMIN">Admin</option>
          <option value="EDITOR">Editor</option>
          <option value="VIEWER">Viewer</option>
        </select>
      </div>

      <div className="flex gap-2 pt-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {saving ? "Saving..." : isEdit ? "Save Changes" : "Create User"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
