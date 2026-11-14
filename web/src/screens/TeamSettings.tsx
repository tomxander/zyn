import { Drawer } from "../components/Drawer";
import { Loading } from "../components/Loader";
import { Button, Chip, Msg, Section, Table } from "../components/ui";
import { useTeamSettings } from "../lib/api";

export function TeamSettingsDrawer({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const settings = useTeamSettings();
  const data = settings.data;

  const projectsRows = data?.projects
    ? Object.entries(data.projects as Record<string, any>).map(([id, p]) => ({
        id,
        name: p.name,
        profile: p.rule_profile,
        four_eyes: p.four_eyes ? "Yes" : "No",
        roles: Object.entries(p.roles || {})
          .map(([r, g]) => `${r}: ${(g as string[]).join(", ")}`)
          .join(" · "),
      }))
    : [];

  const serviceAccountRows = data?.service_accounts
    ? Object.entries(data.service_accounts as Record<string, any>).map(([name, sa]) => ({
        name,
        project: sa.project,
        role: sa.role,
        token: sa.token_sha256 === "set" ? "Configured" : "Missing",
      }))
    : [];

  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title="Team settings"
      description="Server configuration and project permissions (read-only)."
      footer={
        <Button variant="ghost" onClick={() => onOpenChange(false)}>
          Close
        </Button>
      }
    >
      <div className="stack-lg">
        {settings.isLoading ? (
          <Loading label="Loading settings" />
        ) : settings.isError ? (
          <Msg tone="bad">{(settings.error as Error).message}</Msg>
        ) : data ? (
          <>
            <Section title="General" hint="Core server runtime settings" />
            <div className="stack-sm">
              <p className="small">Public URL: <code>{data.public_url}</code></p>
              <p className="small">Database: <code>{data.database_url}</code></p>
              <p className="small">Token lifetime limit: <code>{data.token_days} days</code></p>
              <p className="small">Max upload size: <code>{data.max_upload_mb} MB</code></p>
              <p className="small">
                Insecure HTTP allowed:{" "}
                <Chip tone={data.allow_insecure_http ? "warn" : "ok"}>
                  {data.allow_insecure_http ? "Yes (trial)" : "No (HTTPS only)"}
                </Chip>
              </p>
            </div>

            {data.oidc && (
              <>
                <Section title="Sign-in (OIDC)" hint="OpenID Connect provider settings" />
                <div className="stack-sm">
                  <p className="small">Issuer: <code>{data.oidc.issuer}</code></p>
                  <p className="small">Client ID: <code>{data.oidc.client_id}</code></p>
                  <p className="small">Client secret: <code>{data.oidc.client_secret}</code></p>
                </div>
              </>
            )}

            <Section title="Projects" hint="Configured team projects and permissions" />
            {projectsRows.length > 0 ? (
              <Table
                rows={projectsRows}
                cols={[
                  { key: "id", label: "ID", mono: true },
                  { key: "name", label: "Name" },
                  { key: "profile", label: "Profile", mono: true },
                  { key: "four_eyes", label: "Four-eyes" },
                  { key: "roles", label: "Roles" },
                ]}
              />
            ) : (
              <p className="small quiet">No projects configured.</p>
            )}

            {serviceAccountRows.length > 0 && (
              <>
                <Section title="Service accounts" hint="Machine tokens for CI and test benches" />
                <Table
                  rows={serviceAccountRows}
                  cols={[
                    { key: "name", label: "Account", mono: true },
                    { key: "project", label: "Project", mono: true },
                    { key: "role", label: "Role" },
                    { key: "token", label: "Token" },
                  ]}
                />
              </>
            )}
          </>
        ) : null}
      </div>
    </Drawer>
  );
}
