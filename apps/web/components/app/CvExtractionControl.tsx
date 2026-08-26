import { CvDocument, CvExtraction } from "@/lib/api-client";

interface CvExtractionControlProps {
  document: CvDocument;
  extraction: CvExtraction | null | undefined;
  isStarting: boolean;
  statusError: string | null;
  onStart: (document: CvDocument) => void;
}

function statusLabel(extraction: CvExtraction | null | undefined): string {
  if (!extraction) {
    return "Not prepared";
  }
  if (extraction.readiness.state === "ready") {
    return "Ready";
  }
  if (extraction.readiness.state === "warning") {
    return "Ready with limitations";
  }
  if (extraction.readiness.state === "blocked") {
    return "Blocked";
  }
  if (extraction.status === "failed") {
    return "Preparation needs attention";
  }
  return "Preparing text";
}

function statusDescription(extraction: CvExtraction | null | undefined): string {
  if (!extraction) {
    return "Create a private text-only working copy. Private text is kept on the server and is not shown here.";
  }
  if (extraction.status === "pending" || extraction.status === "processing") {
    return "CVMatcher is preparing private text from this version. Keep this page open.";
  }
  return extraction.readiness.explanation;
}

function readinessBadgeClass(extraction: CvExtraction | null | undefined): string | null {
  if (extraction?.readiness.state === "ready") {
    return "bg-emerald-50 text-success";
  }
  if (extraction?.readiness.state === "warning") {
    return "bg-amber-50 text-amber-900";
  }
  if (extraction?.readiness.state === "blocked") {
    return "bg-red-50 text-danger";
  }
  return null;
}

export function CvExtractionControl({
  document,
  extraction,
  isStarting,
  statusError,
  onStart,
}: CvExtractionControlProps) {
  const isPreparing = isStarting || extraction?.status === "pending" || extraction?.status === "processing";
  const canStartPreparation = !extraction || extraction.status === "failed";
  const badgeClass = readinessBadgeClass(extraction);
  const recoveryGuidance = extraction?.readiness.recoveryGuidance;

  return (
    <section
      aria-label={`CV text preparation for ${document.title}`}
      className="mt-4 border-t border-line pt-4 sm:mt-0 sm:min-w-72 sm:border-l sm:border-t-0 sm:pl-5 sm:pt-0"
    >
      <div aria-live="polite" className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-ink">{statusLabel(extraction)}</p>
        {badgeClass ? (
          <span className={`rounded-sm px-2.5 py-1 text-xs font-semibold ${badgeClass}`}>
            PRIVATE WORKING COPY
          </span>
        ) : null}
      </div>
      <p className="mt-1 max-w-sm text-sm leading-6 text-ink-muted">{statusDescription(extraction)}</p>
      {recoveryGuidance ? (
        <p className="mt-3 rounded-sm border border-amber-300 bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-900" role="status">
          {recoveryGuidance}
        </p>
      ) : null}
      {statusError ? (
        <p className="mt-3 rounded-sm border border-danger/30 bg-red-50 px-3 py-2 text-sm leading-6 text-danger" role="alert">
          {statusError}
        </p>
      ) : null}
      {canStartPreparation ? (
        <button
          className="mt-3 rounded-sm border border-brand px-3 py-2 text-sm font-semibold text-brand transition hover:bg-brand hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isPreparing}
          onClick={() => onStart(document)}
          type="button"
        >
          {isPreparing ? "Preparing CV text…" : extraction?.status === "failed" ? "Try preparation again" : "Prepare CV text"}
        </button>
      ) : null}
    </section>
  );
}
