import { api } from "../lib/api";
import { Button, Chip, Select } from "../components/ui";

export interface ProjectRole {
  id: string;
  name: string;
  role: string;
  four_eyes: boolean;
}

export function PersonMenu({
  person,
  projects,
  currentProject,
  onSelectProject,
  onOpenTokens,
  onOpenSettings,
  isAdmin,
}: {
  person: { name: string; email?: string | null };
  projects: ProjectRole[];
  currentProject: string | null;
  onSelectProject: (id: string) => void;
  onOpenTokens: () => void;
  onOpenSettings?: () => void;
  isAdmin?: boolean;
}) {
  const current = projects.find((p) => p.id === currentProject) || projects[0];
  const roleName = current?.role
    ? current.role.charAt(0).toUpperCase() + current.role.slice(1)
    : "";

  return (
    <div className="person-menu stack-sm">
      <div className="person-menu-head">
        <div>
          <b>{person.name}</b>
          {person.email && <p className="side-hint">{person.email}</p>}
        </div>
        {current && <Chip tone="muted">{roleName}</Chip>}
      </div>

      {projects.length > 1 && (
        <div className="person-menu-projects">
          <Select
            value={current?.id}
            label="Project"
            onChange={(val) => val && onSelectProject(val)}
            options={projects.map((p) => ({ value: p.id, label: `${p.name} (${p.role.charAt(0).toUpperCase() + p.role.slice(1)})` }))}
          />
        </div>
      )}

      <div className="person-menu-actions">
        <Button variant="ghost" size="sm" onClick={onOpenTokens}>
          Access tokens
        </Button>
        {isAdmin && onOpenSettings && (
          <Button variant="ghost" size="sm" onClick={onOpenSettings}>
            Team settings
          </Button>
        )}
        <span className="grow" />
        <Button
          variant="ghost"
          size="sm"
          onClick={async () => {
            try {
              await api("/auth/logout", { method: "POST" });
            } catch {
              // signed out or not, the start page shows the current state
            } finally {
              window.location.href = "/";
            }
          }}
        >
          Sign out
        </Button>
      </div>
    </div>
  );
}
