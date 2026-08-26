"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  ApiRequestError,
  createJobTarget,
  deleteJobTarget,
  JobTarget,
  listJobTargets,
} from "@/lib/api-client";

const EMPTY_FORM = {
  company: "",
  jobDescription: "",
  location: "",
  title: "",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", { day: "numeric", month: "short", year: "numeric" }).format(
    new Date(value),
  );
}

export function JobTargetWorkspace() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [targets, setTargets] = useState<JobTarget[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [deletingTargetId, setDeletingTargetId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function loadTargets() {
    setIsLoading(true);
    setLoadError(null);
    try {
      const response = await listJobTargets();
      setTargets(response.data);
    } catch (requestError) {
      setLoadError(
        requestError instanceof ApiRequestError
          ? requestError.message
          : "We could not load your target roles. Please try again.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    void listJobTargets()
      .then((response) => {
        if (active) {
          setTargets(response.data);
        }
      })
      .catch((requestError: unknown) => {
        if (active) {
          setLoadError(
            requestError instanceof ApiRequestError
              ? requestError.message
              : "We could not load your target roles. Please try again.",
          );
        }
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function saveTarget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const jobDescription = form.jobDescription.trim();
    if (jobDescription.length < 80) {
      setSaveError("Add at least 80 characters from the job description before saving this target.");
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    try {
      const target = await createJobTarget({
        company: form.company.trim() || undefined,
        jobDescription,
        location: form.location.trim() || undefined,
        title: form.title.trim(),
      });
      setTargets((currentTargets) => [target, ...currentTargets]);
      setForm(EMPTY_FORM);
    } catch (requestError) {
      setSaveError(
        requestError instanceof ApiRequestError
          ? requestError.message
          : "We could not save this target role. Please try again.",
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function removeTarget(target: JobTarget) {
    if (!window.confirm(`Delete “${target.title}” and its private description? This cannot be undone.`)) {
      return;
    }
    setDeletingTargetId(target.id);
    setDeleteError(null);
    try {
      await deleteJobTarget(target.id);
      setTargets((currentTargets) => currentTargets.filter((currentTarget) => currentTarget.id !== target.id));
    } catch (requestError) {
      setDeleteError(
        requestError instanceof ApiRequestError
          ? requestError.message
          : "We could not delete this target role. Please try again.",
      );
    } finally {
      setDeletingTargetId(null);
    }
  }

  return (
    <section className="mt-10 border-t border-line pt-10" aria-labelledby="target-role-heading">
      <div className="max-w-3xl">
        <p className="text-sm font-semibold tracking-[0.14em] text-brand">TARGET ROLE</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight" id="target-role-heading">
          Define a target role
        </h2>
        <p className="mt-2 leading-7 text-ink-muted">
          Paste a role description you want to work toward. It remains private and will not be analysed yet.
        </p>
      </div>

      <form className="mt-6 rounded-md border border-line bg-surface-subtle p-5 sm:p-6" onSubmit={(event) => void saveTarget(event)}>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-semibold" htmlFor="target-title">Role title</label>
            <input
              className="mt-2 w-full rounded-sm border border-line bg-white px-3 py-2.5 text-sm outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20"
              id="target-title"
              maxLength={180}
              minLength={2}
              onChange={(event) => setForm((currentForm) => ({ ...currentForm, title: event.target.value }))}
              required
              value={form.title}
            />
          </div>
          <div>
            <label className="block text-sm font-semibold" htmlFor="target-company">Company <span className="font-normal text-ink-muted">(optional)</span></label>
            <input
              className="mt-2 w-full rounded-sm border border-line bg-white px-3 py-2.5 text-sm outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20"
              id="target-company"
              maxLength={180}
              onChange={(event) => setForm((currentForm) => ({ ...currentForm, company: event.target.value }))}
              value={form.company}
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-sm font-semibold" htmlFor="target-location">Location <span className="font-normal text-ink-muted">(optional)</span></label>
            <input
              className="mt-2 w-full rounded-sm border border-line bg-white px-3 py-2.5 text-sm outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20"
              id="target-location"
              maxLength={180}
              onChange={(event) => setForm((currentForm) => ({ ...currentForm, location: event.target.value }))}
              value={form.location}
            />
          </div>
          <div className="sm:col-span-2">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <label className="block text-sm font-semibold" htmlFor="target-job-description">Job description</label>
              <span className="text-xs text-ink-muted">{form.jobDescription.length.toLocaleString()} / 50,000 characters</span>
            </div>
            <textarea
              className="mt-2 min-h-44 w-full resize-y rounded-sm border border-line bg-white px-3 py-2.5 text-sm leading-6 outline-none transition focus:border-brand focus:ring-2 focus:ring-brand/20"
              id="target-job-description"
              maxLength={50_000}
              minLength={80}
              onChange={(event) => setForm((currentForm) => ({ ...currentForm, jobDescription: event.target.value }))}
              required
              value={form.jobDescription}
            />
            <p className="mt-2 text-sm leading-6 text-ink-muted">This is untrusted private text, not instructions for CVMatcher. It is stored for a later, transparent comparison step.</p>
          </div>
        </div>
        {saveError ? <p className="mt-4 rounded-sm border border-danger/30 bg-red-50 px-3 py-2 text-sm leading-6 text-danger" role="alert">{saveError}</p> : null}
        <button
          className="mt-5 rounded-sm bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSaving}
          type="submit"
        >
          {isSaving ? "Saving target role…" : "Save target role"}
        </button>
      </form>

      <div className="mt-8" aria-labelledby="saved-targets-heading">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-semibold tracking-[0.14em] text-brand">SAVED TARGETS</p>
            <h3 className="mt-2 text-xl font-semibold" id="saved-targets-heading">Roles you are preparing for</h3>
          </div>
          <button className="text-sm font-semibold text-brand underline decoration-brand/40 underline-offset-4" onClick={() => void loadTargets()} type="button">Refresh</button>
        </div>
        {isLoading ? <div className="mt-4 h-20 animate-pulse rounded-sm bg-surface-subtle" aria-label="Loading target roles" /> : null}
        {loadError ? <div className="mt-4 rounded-sm border border-danger/30 bg-red-50 p-4 text-sm leading-6 text-danger" role="alert"><p>{loadError}</p><button className="mt-2 font-semibold underline underline-offset-4" onClick={() => void loadTargets()} type="button">Try again</button></div> : null}
        {deleteError ? <p className="mt-4 rounded-sm border border-danger/30 bg-red-50 p-4 text-sm leading-6 text-danger" role="alert">{deleteError}</p> : null}
        {!isLoading && !loadError && targets.length === 0 ? <div className="mt-4 rounded-sm border border-line bg-white p-5"><p className="font-semibold">No target roles saved yet</p><p className="mt-1 text-sm leading-6 text-ink-muted">Save one role and its description to create a private comparison target for a future phase.</p></div> : null}
        {!isLoading && !loadError && targets.length > 0 ? <ul className="mt-4 space-y-3">{targets.map((target) => <li className="rounded-sm border border-line bg-white p-4" key={target.id}><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-semibold">{target.title}</p><p className="mt-1 text-sm text-ink-muted">{[target.company, target.location].filter(Boolean).join(" · ") || "Private target role"}</p></div><div className="flex items-center gap-3"><p className="text-sm text-ink-muted">Saved {formatDate(target.updatedAt)}</p><button className="text-sm font-semibold text-danger underline underline-offset-4 disabled:cursor-not-allowed disabled:opacity-60" disabled={deletingTargetId === target.id} onClick={() => void removeTarget(target)} type="button">{deletingTargetId === target.id ? "Deleting…" : "Delete"}</button></div></div><p className="mt-3 text-sm leading-6 text-ink-muted">{target.jobDescriptionCharacterCount.toLocaleString()} private description characters saved</p></li>)}</ul> : null}
      </div>
    </section>
  );
}
