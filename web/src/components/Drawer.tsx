// Side panel for edit forms and new runs. Slides in from the right; drag or Esc to close.

import { X } from "./icons";
import type { ReactNode } from "react";
import { Drawer as V } from "vaul";
import { Button } from "./ui";

export function Drawer({ open, onOpenChange, title, description, children, footer }: {
  open: boolean; onOpenChange: (v: boolean) => void; title: string; description?: string;
  children: ReactNode; footer?: ReactNode;
}) {
  return (
    <V.Root open={open} onOpenChange={onOpenChange} direction="right" handleOnly>
      <V.Portal>
        <V.Overlay className="overlay" />
        <V.Content className="drawer" {...(description ? {} : { "aria-describedby": undefined })}
          onOpenAutoFocus={(e) => {
            // Start in the first field, not on the close button.
            const field = (e.currentTarget as HTMLElement).querySelector<HTMLElement>(
              ".drawer-body textarea, .drawer-body input:not([type=file]), .drawer-body button");
            if (field) { e.preventDefault(); field.focus(); }
          }}
          onKeyDown={(e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
              (e.currentTarget as HTMLElement).querySelector<HTMLButtonElement>(".drawer-foot .btn-primary:not(:disabled)")?.click();
            }
          }}>
          <div className="drawer-head">
            <div className="grow">
              <V.Title asChild><h2>{title}</h2></V.Title>
              {description && <V.Description asChild><p>{description}</p></V.Description>}
            </div>
            <Button variant="ghost" size="sm" icon={X} aria-label="Close" onClick={() => onOpenChange(false)} />
          </div>
          <div className="drawer-body">{children}</div>
          {footer && <div className="drawer-foot">{footer}</div>}
        </V.Content>
      </V.Portal>
    </V.Root>
  );
}
