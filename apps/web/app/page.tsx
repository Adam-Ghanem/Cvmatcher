const foundationCards = [
  {
    title: "Your evidence",
    description: "Your CV will remain yours. Future document workflows are designed around private storage and clear ownership.",
  },
  {
    title: "The target role",
    description: "A role brief will become a transparent set of requirements, not a black-box keyword list.",
  },
  {
    title: "The next move",
    description: "Results will prioritise what matters, why it matters, and the action you can take next.",
  },
] as const;

export default function HomePage() {
  return (
    <main className="min-h-screen bg-canvas px-4 py-4 text-ink sm:px-6 lg:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-2rem)] max-w-6xl flex-col rounded-md border border-line bg-surface shadow-panel">
        <header className="flex items-center justify-between border-b border-line px-5 py-4 sm:px-8">
          <a className="inline-flex items-center gap-3 font-semibold tracking-tight" href="#main-content">
            <span aria-hidden="true" className="grid size-8 place-items-center rounded-sm bg-brand text-sm font-bold text-white">
              C
            </span>
            <span>CVMatcher</span>
          </a>
          <span className="rounded-sm bg-brand-soft px-3 py-1 text-xs font-semibold tracking-wide text-brand-strong">
            FOUNDATION
          </span>
        </header>

        <section id="main-content" className="grid flex-1 gap-10 px-5 py-12 sm:px-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-center lg:gap-16 lg:px-14 lg:py-16">
          <div>
            <p className="mb-5 text-sm font-semibold tracking-[0.16em] text-brand">CAREER INTELLIGENCE</p>
            <h1 className="max-w-3xl text-4xl font-semibold tracking-[-0.045em] text-balance sm:text-5xl lg:text-6xl">
              See the distance between where you are and where you want to go.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-ink-muted">
              CVMatcher is being built to turn a CV and a target role into explainable strengths, meaningful gaps, and a credible plan of action.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <span className="rounded-sm border border-line px-3 py-2 text-sm font-medium">Transparent scoring</span>
              <span className="rounded-sm border border-line px-3 py-2 text-sm font-medium">Private by design</span>
              <span className="rounded-sm border border-line px-3 py-2 text-sm font-medium">Action-oriented</span>
            </div>
          </div>

          <aside className="rounded-md border border-line bg-surface-subtle p-5 sm:p-6" aria-label="Phase 1 progress">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-brand">Product foundation</p>
                <h2 className="mt-1 text-2xl font-semibold tracking-tight">Building the system of trust</h2>
              </div>
              <span className="rounded-sm bg-white px-2.5 py-1 text-xs font-semibold text-ink-muted">Phase 1</span>
            </div>
            <ol className="mt-7 space-y-4 border-l border-brand pl-5 text-sm">
              <li>
                <p className="font-semibold">Secure ownership boundaries</p>
                <p className="mt-1 leading-6 text-ink-muted">Identity-aware data and API foundations are being prepared before customer documents exist.</p>
              </li>
              <li>
                <p className="font-semibold">Explainable analysis contract</p>
                <p className="mt-1 leading-6 text-ink-muted">Future scoring will be deterministic, versioned, and grounded in visible evidence.</p>
              </li>
              <li>
                <p className="font-semibold">Accessible product language</p>
                <p className="mt-1 leading-6 text-ink-muted">The interface starts with clarity, responsive structure, and keyboard-friendly semantics.</p>
              </li>
            </ol>
          </aside>
        </section>

        <section className="border-t border-line px-5 py-8 sm:px-8 lg:px-14" aria-labelledby="principles-heading">
          <h2 id="principles-heading" className="sr-only">Product principles</h2>
          <div className="grid gap-4 md:grid-cols-3">
            {foundationCards.map((card, index) => (
              <article className="rounded-sm border border-line p-5" key={card.title}>
                <p className="text-xs font-semibold tracking-[0.16em] text-brand">0{index + 1}</p>
                <h3 className="mt-3 text-lg font-semibold">{card.title}</h3>
                <p className="mt-2 leading-6 text-ink-muted">{card.description}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
