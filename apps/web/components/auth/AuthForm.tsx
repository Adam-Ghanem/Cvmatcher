"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ApiRequestError, apiFetch, getCsrfToken } from "@/lib/api-client";

type AuthMode = "login" | "register";

interface AuthFormProps {
  mode: AuthMode;
}

const CONTENT: Record<AuthMode, { title: string; intro: string; action: string; alternate: string; href: string; link: string }> = {
  login: {
    title: "Welcome back",
    intro: "Sign in to continue managing your private CV documents.",
    action: "Sign in",
    alternate: "New to CVMatcher?",
    href: "/auth/register",
    link: "Create an account",
  },
  register: {
    title: "Create your secure workspace",
    intro: "Your documents remain private and are always linked to your account.",
    action: "Create account",
    alternate: "Already have an account?",
    href: "/auth/login",
    link: "Sign in",
  },
};

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const content = CONTENT[mode];
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setError(null);
    setIsSubmitting(true);

    try {
      const csrfToken = await getCsrfToken();
      await apiFetch(`/api/v1/auth/${mode === "login" ? "login" : "register"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
        body: JSON.stringify({
          email: String(formData.get("email") ?? ""),
          password: String(formData.get("password") ?? ""),
        }),
      });
      router.replace("/app");
      router.refresh();
    } catch (requestError) {
      setError(
        requestError instanceof ApiRequestError
          ? requestError.message
          : "We could not complete this request. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-canvas px-4 py-4 text-ink sm:px-6 lg:px-8">
      <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-5xl overflow-hidden rounded-md border border-line bg-surface shadow-panel lg:grid-cols-[0.9fr_1.1fr]">
        <section className="bg-brand px-6 py-10 text-white sm:px-10 lg:p-12">
          <Link className="inline-flex items-center gap-3 font-semibold tracking-tight" href="/">
            <span aria-hidden="true" className="grid size-8 place-items-center rounded-sm bg-white text-sm font-bold text-brand">
              C
            </span>
            <span>CVMatcher</span>
          </Link>
          <div className="mt-16 max-w-sm lg:mt-28">
            <p className="text-sm font-semibold tracking-[0.16em] text-brand-soft">PRIVATE WORKSPACE</p>
            <h1 className="mt-4 text-3xl font-semibold tracking-[-0.035em] sm:text-4xl">
              Career intelligence begins with control.
            </h1>
            <p className="mt-5 leading-7 text-white/75">
              Your CV is sensitive. CVMatcher is designed to keep your documents private, owned by you, and ready for clear next steps.
            </p>
          </div>
        </section>

        <section className="flex items-center px-6 py-10 sm:px-10 lg:p-12">
          <div className="w-full max-w-md">
            <p className="text-sm font-semibold tracking-[0.14em] text-brand">ACCOUNT</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em]">{content.title}</h2>
            <p className="mt-3 leading-7 text-ink-muted">{content.intro}</p>

            <form className="mt-8 space-y-5" onSubmit={handleSubmit} noValidate>
              <div>
                <label className="block text-sm font-semibold" htmlFor="email">
                  Email address
                </label>
                <input
                  autoComplete="email"
                  className="mt-2 w-full rounded-sm border border-line bg-white px-3 py-3 text-base shadow-sm outline-none transition focus:border-brand"
                  id="email"
                  name="email"
                  required
                  type="email"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold" htmlFor="password">
                  Password
                </label>
                <input
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  className="mt-2 w-full rounded-sm border border-line bg-white px-3 py-3 text-base shadow-sm outline-none transition focus:border-brand"
                  id="password"
                  minLength={12}
                  name="password"
                  required
                  type="password"
                />
                {mode === "register" ? (
                  <p className="mt-2 text-sm leading-6 text-ink-muted">Use at least 12 characters. We never store your password in plain text.</p>
                ) : null}
              </div>

              {error ? (
                <div className="rounded-sm border border-danger/30 bg-red-50 px-3 py-3 text-sm leading-6 text-danger" role="alert">
                  {error}
                </div>
              ) : null}

              <button
                className="w-full rounded-sm bg-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isSubmitting}
                type="submit"
              >
                {isSubmitting ? "Securing your session…" : content.action}
              </button>
            </form>

            <p className="mt-7 text-sm text-ink-muted">
              {content.alternate}{" "}
              <Link className="font-semibold text-brand underline decoration-brand/40 underline-offset-4" href={content.href}>
                {content.link}
              </Link>
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
