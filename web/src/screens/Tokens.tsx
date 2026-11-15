import { useState } from "react";
import { toast } from "sonner";
import { Drawer } from "../components/Drawer";
import { Badge, Button, Empty, Field, Msg, Section } from "../components/ui";
import { Loading } from "../components/Loader";
import { useCreateToken, useRevokeToken, useTokens } from "../lib/api";

export function TokensDrawer({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const tokens = useTokens(open);
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

  // Revoking asks once, in place, naming the token (no browser dialog).
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const handleRevoke = async (tokenId: string) => {
    setRevokingId(tokenId);
    try {
      await revokeMutation.mutateAsync(tokenId);
      setConfirmId(null);
    } catch {
      // the mutation already shows the error
    } finally {
      setRevokingId(null);
    }
  };

  const list = Array.isArray(tokens.data) ? tokens.data : [];
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
          <div className="token-box stack-sm">
            <Section title="New access token" hint="Copy it now. You will not see it again." />
            <code className="token-secret">{createdSecret}</code>
            <div className="row">
              <Button variant="primary" size="sm" onClick={handleCopy}>Copy token</Button>
              <Button variant="ghost" size="sm" onClick={() => setCreatedSecret(null)}>Dismiss</Button>
            </div>
          </div>
        )}

        <div className="stack-sm">
          <Section title="Create token" hint="Each token is valid for 90 days." />
          <Field label="Token description or purpose">
            <input className="input" placeholder="CI pipeline on GitLab, HIL bench test runner"
              value={label} onChange={(e) => setLabel(e.target.value)} />
          </Field>
          <div>
            {/* while a new secret is on screen, Copy token is the one primary action */}
            <Button variant={createdSecret ? "plain" : "primary"} size="sm"
              disabled={!label.trim() || createMutation.isPending}
              tip={!label.trim() ? "Describe what the token is for first" : undefined}
              onClick={handleCreate}>Create token</Button>
          </div>
        </div>

        <div className="stack-sm">
          <Section title={`Active tokens (${activeTokens.length})`} />
          {tokens.isLoading ? (
            <Loading label="Loading tokens" />
          ) : tokens.isError ? (
            <Msg tone="bad">{(tokens.error as Error).message}</Msg>
          ) : activeTokens.length === 0 ? (
            <Empty title="No active tokens" body="Create one for scripts and test benches." />
          ) : (
            <div className="stack-sm">
              {activeTokens.map((tok) => (
                <div key={tok.token_id} className="token-box token-item">
                  <div className="stack-xs">
                    <b>{tok.label}</b>
                    <p className="small quiet">Created {tok.created_at.slice(0, 10)} · expires {tok.expires_at.slice(0, 10)}</p>
                  </div>
                  <div className="token-actions">
                    <Badge text="active" tone="ok" />
                    {confirmId === tok.token_id ? (
                      <>
                        <span className="small">Scripts using it stop working.</span>
                        <Button size="sm" busy={revokingId === tok.token_id}
                          onClick={() => handleRevoke(tok.token_id)}>Revoke {tok.label}</Button>
                        <Button variant="ghost" size="sm" onClick={() => setConfirmId(null)}>Keep</Button>
                      </>
                    ) : (
                      <Button variant="ghost" size="sm" onClick={() => setConfirmId(tok.token_id)}>Revoke</Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {revokedTokens.length > 0 && (
          <div className="stack-sm">
            <Section title={`Revoked tokens (${revokedTokens.length})`} />
            {revokedTokens.map((tok) => (
              <div key={tok.token_id} className="token-box token-item">
                <div className="stack-xs">
                  <b>{tok.label}</b>
                  <p className="small quiet">Created {tok.created_at.slice(0, 10)} · expires {tok.expires_at.slice(0, 10)}</p>
                </div>
                <div className="token-actions"><Badge text="revoked" tone="muted" /></div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Drawer>
  );
}
