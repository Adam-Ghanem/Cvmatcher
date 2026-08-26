"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  ApiRequestError,
  createMatchAnalysis,
  CvDocument,
  CvExtraction,
  JobTarget,
  listJobTargets,
  MatchAnalysis,
  MatchScoreComponent,
} from "@/lib/api-client";

interface AnalysisWorkspaceProps {
  documents: CvDocument[];
  extractions: Record<string, CvExtraction | null>;
  isDocumentsLoading: boolean;
}

function targetLabel(target: JobTarget): string {
  return [target.title, target.company, target.location].filter(Boolean).join(" · ");
}

function componentStateLabel(state: MatchScoreComponent["state"]): string {
  const labels: Record<MatchScoreComponent["state"], string> = {
    EVIDENCE_NOT_FOUND: "Not found in the provided CV",
    MATCHED: "Evidence found",
    NOT_APPLICABLE: "No target signal to compare",
    PARTIAL: "Partially evidenced",
  };
  return labels[state];
}

function ComponentEvidence({ component }: { component: MatchScoreComponent }) {
  return (
    <li className="border-t border-line py-4 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h4 className="font-semibold">{component.label}</h4>
          <p className="mt-1 text-sm leading-6 text-ink-muted">{component.explanation}</p>
        </div>
        <div className="text-right">
          <p className="text-lg font-semibold tabular-nums text-ink">{component.score}%</p>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-ink-muted">
            {component.weight}% weight
          </p>
        </div>
      </div>
      <p className="mt-3 text-sm font-medium text-ink">{componentStateLabel(component.state)}</p>
      {component.matchedTerms.length > 0 ? (
        <p className="mt-2 text-sm leading-6 text-ink-muted">
          <span className="font-semibold text-ink">Evidence found: </span>
          {component.matchedTerms.join(", ")}
        </p>
      ) : null}
      {component.notFoundTerms.length > 0 ? (
        <p className="mt-2 text-sm leading-6 text-ink-muted">
          <span className="font-semibold text-ink">Not found in the provided CV: </span>
          {component.notFoundTerms.join(", ")}
        </p>
      ) : null}
    </li>
  );
}

export function AnalysisWorkspace({
  documents,
  extractions,
  isDocumentsLoading,
}: AnalysisWorkspaceProps) {
  const resultRef = useRef<HTMLDivElement>(null);
  const [targets, setTargets] = useState<JobTarget[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState("");
  const [selectedTargetId, setSelectedTargetId] = useState("");
  const [isLoadingTargets, setIsLoadingTargets] = useState(true);
  const [targetError, setTargetError] = useState<string | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [analysis, setAnalysis] = useState<MatchAnalysis | null>(null);

  const preparedDocuments = useMemo(
    () => documents.filter((document) => {
      const extraction = extractions[document.latestVersion.id];
      return extraction?.status === "succeeded" && extraction.quality === "usable";
    }),
    [documents, extractions],
  );

  async function loadTargets() {
    setIsLoadingTargets(true);
    setTargetError(null);
    try {
      const response = await listJobTargets();
      setTargets(response.data);
    } catch (requestError) {
      setTargetError(
        requestError instanceof ApiRequestError
          ? requestError.message
          : "We could not load your target roles. Refresh and try again.",
      );
    } finally {
      setIsLoadingTargets(false);
    }
  }

  useEffect(() => {
    let active = true;
    void listJobTargets()
      .then((response) => {
        if (active) {
          setTargets(response.data);
          setTargetError(null);
        }
      })
      .catch((requestError: unknown) => {
        if (active) {
          setTargetError(
            requestError instanceof ApiRequestError
              ? requestError.message
              : "We could not load your target roles. Refresh and try again.",
          );
        }
      })
      .finally(() => {
        if (active) {
          setIsLoadingTargets(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function submitAnalysis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedVersionId || !selectedTargetId) {
      setSubmissionError("Choose one prepared CV and one saved target role before creating a match.");
      return;
    }

    setIsSubmitting(true);
    setSubmissionError(null);
    try {
      const result = await createMatchAnalysis({
        cvDocumentVersionId: selectedVersionId,
        jobTargetId: selectedTargetId,
      });
      setAnalysis(result);
      requestAnimationFrame(() => resultRef.current?.focus());
    } catch (requestError) {
      setSubmissionError(
        requestError instanceof ApiRequestError
          ? requestError.message
          : "We could not create this evidence match. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  const canSubmit = preparedDocuments.length > 0 && targets.length > 0 && !isSubmitting;

  return (
    <section className="mt-10 border-t border-line pt-10" aria-labelledby="analysis-heading">
      <div className="max-w-3xl">
        <p className="text-sm font-semibold tracking-[0.14em] text-brand">EVIDENCE MATCH</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight" id="analysis-heading">
          Compare the evidence
        </h2>
        <p className="mt-2 leading-7 text-ink-muted">
          Pair a prepared CV with a saved target role to see an explainable, deterministic comparison. This is not an interview or employment prediction.
        </p>
      </div>

      <form className="mt-6 rounded-md border border-line bg-surface-subtle p-5 sm:p-6" onSubmit={(event) => void submitAnalysis(event)}>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm font-semibold" htmlFor="analysis-cv-version">Prepared CV</label>
            <select
              className="mt-2 w-full rounded-sm border border-line bg-white px-3 py-2.5 text-sm outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20 disabled:cursor-not-allowed disabled:bg-surface-subtle"
              disabled={isDocumentsLoading || preparedDocuments.length === 0}
              id="analysis-cv-version"
              onChange={(event) => setSelectedVersionId(event.target.value)}
              required
              value={selectedVersionId}
            >
              <option value="">{isDocumentsLoading ? "Checking CV preparation…" : "Choose a prepared CV"}</option>
              {preparedDocuments.map((document) => (
                <option key={document.latestVersion.id} value={document.latestVersion.id}>
                  {document.title} · Version {document.latestVersion.versionNumber}
                </option>
              ))}
            </select>
            {!isDocumentsLoading && preparedDocuments.length === 0 ? (
              <p className="mt-2 text-sm leading-6 text-ink-muted">Prepare a CV with readable text first. Its private text remains on the server.</p>
            ) : null}
          </div>
          <div>
            <div className="flex items-baseline justify-between gap-3">
              <label className="block text-sm font-semibold" htmlFor="analysis-target-role">Target role</label>
              <button
                className="text-xs font-semibold text-brand underline decoration-brand/40 underline-offset-4"
                disabled={isLoadingTargets}
                onClick={() => void loadTargets()}
                type="button"
              >
                Refresh roles
              </button>
            </div>
            <select
              className="mt-2 w-full rounded-sm border border-line bg-white px-3 py-2.5 text-sm outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20 disabled:cursor-not-allowed disabled:bg-surface-subtle"
              disabled={isLoadingTargets || targets.length === 0}
              id="analysis-target-role"
              onChange={(event) => setSelectedTargetId(event.target.value)}
              required
              value={selectedTargetId}
            >
              <option value="">{isLoadingTargets ? "Loading target roles…" : "Choose a saved target role"}</option>
              {targets.map((target) => <option key={target.id} value={target.id}>{targetLabel(target)}</option>)}
            </select>
            {!isLoadingTargets && targets.length === 0 ? (
              <p className="mt-2 text-sm leading-6 text-ink-muted">Save a target role above, then refresh this list to compare it.</p>
            ) : null}
          </div>
        </div>
        {targetError ? <p className="mt-4 rounded-sm border border-danger/30 bg-red-50 px-3 py-2 text-sm leading-6 text-danger" role="alert">{targetError}</p> : null}
        {submissionError ? <p className="mt-4 rounded-sm border border-danger/30 bg-red-50 px-3 py-2 text-sm leading-6 text-danger" role="alert">{submissionError}</p> : null}
        <button
          className="mt-5 rounded-sm bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!canSubmit}
          type="submit"
        >
          {isSubmitting ? "Creating evidence match…" : "Create evidence match"}
        </button>
      </form>

      {analysis ? (
        <div className="mt-8" ref={resultRef} tabIndex={-1}>
          <div className="border-l-4 border-brand bg-surface-subtle p-5 sm:p-6">
            <p className="text-sm font-semibold tracking-[0.14em] text-brand">CURRENT POSITION</p>
            <p className="mt-2 text-3xl font-semibold tracking-[-0.04em] tabular-nums text-ink">{analysis.overallScore}% overall evidence match</p>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-ink-muted">This result shows only normalized comparison evidence. It does not infer experience, credentials, or qualifications that are not found in the provided CV.</p>
          </div>

          <section className="mt-6 rounded-md border border-line bg-white p-5 sm:p-6" aria-labelledby="evidence-detail-heading">
            <h3 className="text-xl font-semibold" id="evidence-detail-heading">What the comparison found</h3>
            <ul className="mt-5"><>{analysis.components.map((component) => <ComponentEvidence component={component} key={component.key} />)}</></ul>
          </section>

          <section className="mt-6 rounded-md border border-line bg-white p-5 sm:p-6" aria-labelledby="gaps-heading">
            <h3 className="text-xl font-semibold" id="gaps-heading">Priorities to examine</h3>
            {analysis.gaps.length > 0 ? (
              <ul className="mt-4 space-y-3">
                {analysis.gaps.map((gap) => (
                  <li className="border-l-2 border-line pl-3 text-sm leading-6 text-ink-muted" key={`${gap.component}-${gap.term}`}>
                    <span className="font-semibold text-ink">{gap.term}</span> — Not found in the provided CV ({gap.component.replace(/_/g, " ")}).
                  </li>
                ))}
              </ul>
            ) : <p className="mt-3 text-sm leading-6 text-ink-muted">No bounded target terms were marked as not found in the provided CV.</p>}
          </section>

          <details className="mt-6 rounded-md border border-line bg-surface-subtle p-5">
            <summary className="cursor-pointer font-semibold">How we calculated this</summary>
            <p className="mt-3 text-sm leading-6 text-ink-muted">The {analysis.scoringVersion} comparison combines skills (35%), experience evidence (20%), target keywords (25%), education evidence (10%), and ATS-ready structure signals (10%). A component with no target signal is marked not applicable rather than reducing the score. The score is reproducible from fixed, source-controlled rules and is not an AI or hiring score.</p>
          </details>
        </div>
      ) : null}
    </section>
  );
}
