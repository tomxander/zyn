import { useState } from "react";
import { toast } from "sonner";
import { Drawer } from "../components/Drawer";
import { Button, Chip, Empty, Field, Msg } from "../components/ui";
import { Loading } from "../components/Loader";
import { useCreateToken, useRevokeToken, useTokens } from "../lib/api";

export function TokensDrawer({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const tokens = useTokens();
  const createMutation = useCreateToken();
  const revokeMutation = useRevokeToken();

  const [label, setLabel] = useState("");
  const [createdSecret, setCreatedSecret] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!label.trim()) return;
    try {
      const res = await createMutation.mutateAsync({ label: label.trim(), days: 90 });
      setCreatedSecret(res.secret);
      setLabel("");
    } catch {
      // handled by mutation onError
    }
  };

  const handleCopy = async () => {
    if (!createdSecret) return;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(createdSecret);
      } else {
        const ta = document.createElement("textarea");
        ta.value = createdSecret;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      toast.success("Token copied to clipboard");
    } catch {
      toast.error("Could not copy token automatically; copy it from the box above");
    }
  };

  const handleRevoke = async (tokenId: string) => {
    if (!window.confirm("Revoke this token?")) return;
    setRevokingId(tokenId);
    try {
      await revokeMutation.mutateAsync(tokenId);
    } finally {
      setRevokingId(null);
    }
  };

  const list = tokens.data ?? [];
  const activeTokens = list.filter((t) => !t.revoked);
  const revokedTokens = list.filter((t) => t.revoked);

  return (
    <Drawer
      open={open}
      onOpenChange={(v) => {
        if (!v) setCreatedSecret(null);
        onOpenChange(v);
      }}
      title="Access tokens"
      description="Tokens for CI/CD pipelines, remote test benches, and automation scripts."
    >
      <div className="stack-lg">
        {createdSecret && (
          <div className="card stack-sm">
            <b>New access token</b>
            <code className="token-secret">
              {createdSecret}
            </code>
            <p className="side-hint">
              You will not see this again.
            </p>
            <div className="row">
              <Button variant="primary" size="sm" onClick={handleCopy}>
                Copy token
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setCreatedSecret(null)}>
                Dismiss
              </Button>
            </div>
          </div>
        )}

        <div className="card stack-sm">
          <h3>Create token</h3>
          <Field label="Token description or purpose">
            <input
              className="input"
              placeholder="CI pipeline on GitLab, HIL bench test runner"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
            />
          </Field>
          <div>
            <Button
              variant="primary"
              size="sm"
              disabled={!label.trim() || createMutation.isPending}
              onClick={handleCreate}
            >
              Create token
            </Button>
          </div>
        </div>

        <div className="stack-sm">
          <h3>Active tokens</h3>
          {tokens.isLoading ? (
            <Loading label="Loading tokens" />
          ) : tokens.isError ? (
            <Msg tone="bad">{(tokens.error as Error).message}</Msg>
          ) : activeTokens.length === 0 ? (
            <Empty
              title="No tokens yet"
              body="Create one for scripts and test benches."
            />
          ) : (
            <div className="stack-sm">
              {activeTokens.map((tok) => (
                <div
                  key={tok.token_id}
                  className="card token-item"
                >
                  <div className="stack-xs">
                    <b>{tok.label}</b>
                    <p className="side-hint">
                      Created: {tok.created_at.slice(0, 10)} · Expires: {tok.expires_at.slice(0, 10)}
                    </p>
                  </div>
                  <div className="token-actions">
                    <Chip tone="ok">Active</Chip>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={revokeMutation.isPending && revokingId === tok.token_id}
                      onClick={() => handleRevoke(tok.token_id)}
                    >
                      Revoke
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {revokedTokens.length > 0 && (
          <div className="stack-sm">
            <h3>Revoked tokens</h3>
            <div className="stack-sm">
              {revokedTokens.map((tok) => (
                <div
                  key={tok.token_id}
                  className="card token-item"
                >
                  <div className="stack-xs">
                    <b>{tok.label}</b>
                    <p className="side-hint">
                      Created: {tok.created_at.slice(0, 10)} · Expires: {tok.expires_at.slice(0, 10)}
                    </p>
                  </div>
                  <div className="token-actions">
                    <Chip tone="muted">Revoked</Chip>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Drawer>
  );
}
