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
  if (extraction.status === "succeeded") {
    return "Text prepared";
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
  if (extraction.status === "succeeded") {
    return "A private working copy is ready for a future career analysis. CV text remains server-only.";
  }
  if (extraction.status === "failed") {
    return extraction.failureMessage ?? "We could not prepare this CV. Try again or upload another file.";
  }
  return "CVMatcher is preparing private text from this version. Keep this page open.";
}

export function CvExtractionControl({
  document,
  extraction,
  isStarting,
  statusError,
  onStart,
}: CvExtractionControlProps) {
  const isPrepared = extraction?.status === "succeeded";
  const isPreparing = isStarting || extraction?.status === "pending" || extraction?.status === "processing";
  const needsRetry = extraction?.status === "failed";

  return (
    <section
      aria-label={`CV text preparation for ${document.title}`}
      className="mt-4 border-t border-line pt-4 sm:mt-0 sm:min-w-72 sm:border-l sm:border-t-0 sm:pl-5 sm:pt-0"
    >
      <div aria-live="polite" className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-ink">{statusLabel(extraction)}</p>
        {isPrepared ? (
          <span className="rounded-sm bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-success">
            PRIVATE WORKING COPY
          </span>
        ) : null}
      </div>
      <p className="mt-1 max-w-sm text-sm leading-6 text-ink-muted">{statusDescription(extraction)}</p>
      {extraction?.warnings.includes("NO_EXTRACTABLE_TEXT") ? (
        <p className="mt-3 rounded-sm border border-amber-300 bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-900" role="status">
          We could not find readable text in this file. Upload a text-based PDF or DOCX to use it for comparison.
        </p>
      ) : null}
      {statusError ? (
        <p className="mt-3 rounded-sm border border-danger/30 bg-red-50 px-3 py-2 text-sm leading-6 text-danger" role="alert">
          {statusError}
        </p>
      ) : null}
      {!isPrepared ? (
        <button
          className="mt-3 rounded-sm border border-brand px-3 py-2 text-sm font-semibold text-brand transition hover:bg-brand hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isPreparing}
          onClick={() => onStart(document)}
          type="button"
        >
          {isPreparing ? "Preparing CV text…" : needsRetry ? "Try preparation again" : "Prepare CV text"}
        </button>
      ) : null}
    </section>
  );
}
