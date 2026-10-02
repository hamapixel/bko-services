"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

type AlertTone = "success" | "error" | "warning" | "info";

type AlertMessage = {
  title: string;
  message?: string;
  durationMs?: number;
};

type ConfirmOptions = {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
};

type ToastState = AlertMessage & {
  id: number;
  tone: AlertTone;
};

type DialogState = ConfirmOptions & {
  id: number;
};

type BkoAlertContextValue = {
  success: (message: AlertMessage) => void;
  error: (message: AlertMessage) => void;
  warning: (message: AlertMessage) => void;
  info: (message: AlertMessage) => void;
  confirmAction: (options: ConfirmOptions) => Promise<boolean>;
};

const BkoAlertContext = createContext<BkoAlertContextValue | null>(null);

const ICONS: Record<AlertTone, string> = {
  success: "✓",
  error: "×",
  warning: "!",
  info: "i",
};

export function useBkoAlert() {
  const context = useContext(BkoAlertContext);
  if (!context) {
    throw new Error("useBkoAlert doit être utilisé dans BkoAlertProvider.");
  }
  return context;
}

export default function BkoAlertProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastState | null>(null);
  const [dialog, setDialog] = useState<DialogState | null>(null);
  const counter = useRef(0);
  const confirmResolver = useRef<((value: boolean) => void) | null>(null);
  const confirmButtonRef = useRef<HTMLButtonElement | null>(null);

  const showToast = useCallback((tone: AlertTone, message: AlertMessage) => {
    counter.current += 1;
    setToast({ id: counter.current, tone, ...message });
  }, []);

  const success = useCallback(
    (message: AlertMessage) => showToast("success", message),
    [showToast],
  );
  const error = useCallback(
    (message: AlertMessage) => showToast("error", message),
    [showToast],
  );
  const warning = useCallback(
    (message: AlertMessage) => showToast("warning", message),
    [showToast],
  );
  const info = useCallback(
    (message: AlertMessage) => showToast("info", message),
    [showToast],
  );

  const closeDialog = useCallback((result: boolean) => {
    const resolver = confirmResolver.current;
    confirmResolver.current = null;
    setDialog(null);
    resolver?.(result);
  }, []);

  const confirmAction = useCallback((options: ConfirmOptions) => {
    confirmResolver.current?.(false);
    counter.current += 1;
    setDialog({ id: counter.current, ...options });
    return new Promise<boolean>((resolve) => {
      confirmResolver.current = resolve;
    });
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(
      () => setToast((current) => (current?.id === toast.id ? null : current)),
      toast.durationMs ?? 4200,
    );
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (!dialog) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    confirmButtonRef.current?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") closeDialog(false);
    }

    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [closeDialog, dialog]);

  return (
    <BkoAlertContext.Provider
      value={{ success, error, warning, info, confirmAction }}
    >
      {children}

      <div className="bko-alert-live" aria-live="polite" aria-atomic="true">
        {toast && (
          <div className={`bko-toast bko-toast-${toast.tone}`} role={toast.tone === "error" ? "alert" : "status"}>
            <span className="bko-toast-icon" aria-hidden="true">
              {ICONS[toast.tone]}
            </span>
            <div className="bko-toast-copy">
              <strong>{toast.title}</strong>
              {toast.message && <p>{toast.message}</p>}
            </div>
            <button
              className="bko-toast-close"
              type="button"
              aria-label="Fermer le message"
              onClick={() => setToast(null)}
            >
              ×
            </button>
          </div>
        )}
      </div>

      {dialog && (
        <div
          className="bko-dialog-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeDialog(false);
          }}
        >
          <section
            className={`bko-dialog ${dialog.danger ? "bko-dialog-danger" : ""}`}
            role="alertdialog"
            aria-modal="true"
            aria-labelledby={`bko-dialog-title-${dialog.id}`}
            aria-describedby={`bko-dialog-message-${dialog.id}`}
          >
            <div className="bko-dialog-badge" aria-hidden="true">
              {dialog.danger ? "!" : "✓"}
            </div>
            <div className="bko-dialog-copy">
              <span className="bko-dialog-kicker">BKO Services</span>
              <h2 id={`bko-dialog-title-${dialog.id}`}>{dialog.title}</h2>
              <p id={`bko-dialog-message-${dialog.id}`}>{dialog.message}</p>
            </div>
            <div className="bko-dialog-actions">
              <button
                className="bko-dialog-cancel"
                type="button"
                onClick={() => closeDialog(false)}
              >
                {dialog.cancelLabel ?? "Annuler"}
              </button>
              <button
                ref={confirmButtonRef}
                className={dialog.danger ? "bko-dialog-confirm danger" : "bko-dialog-confirm"}
                type="button"
                onClick={() => closeDialog(true)}
              >
                {dialog.confirmLabel ?? "Confirmer"}
              </button>
            </div>
          </section>
        </div>
      )}
    </BkoAlertContext.Provider>
  );
}
