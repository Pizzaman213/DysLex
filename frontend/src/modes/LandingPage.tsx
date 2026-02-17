import { Link } from 'react-router-dom';
import { useCallback, useState, useEffect, useRef } from 'react';

function useScrollReveal() {
  return useCallback((el: HTMLDivElement | null) => {
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add('landing-visible');
          observer.disconnect();
        }
      },
      { threshold: 0.12 },
    );
    observer.observe(el);
  }, []);
}

/* ---- Live correction demo hook ---- */
const DEMO_ORIGINAL = [
  { text: 'Teh ', err: true },
  { text: 'importent ', err: true },
  { text: 'thing about dyslexia is ', err: false },
  { text: 'taht ', err: true },
  { text: 'it ', err: false },
  { text: 'dosent ', err: true },
  { text: 'mean ', err: false },
  { text: 'your ', err: true },
  { text: 'not smart. ', err: false },
  { text: 'It ', err: false },
  { text: 'menas ', err: true },
  { text: 'you ', err: false },
  { text: 'thnk ', err: true },
  { text: 'diffrent ', err: true },
  { text: '— and ', err: false },
  { text: 'thats ', err: true },
  { text: 'a superpower.', err: false },
];

const DEMO_CORRECTED = [
  { text: 'The ', fixed: true },
  { text: 'important ', fixed: true },
  { text: 'thing about dyslexia is ', fixed: false },
  { text: 'that ', fixed: true },
  { text: 'it ', fixed: false },
  { text: "doesn't ", fixed: true },
  { text: 'mean ', fixed: false },
  { text: "you're ", fixed: true },
  { text: 'not smart. ', fixed: false },
  { text: 'It ', fixed: false },
  { text: 'means ', fixed: true },
  { text: 'you ', fixed: false },
  { text: 'think ', fixed: true },
  { text: 'differently ', fixed: true },
  { text: '— and ', fixed: false },
  { text: "that's ", fixed: true },
  { text: 'a superpower.', fixed: false },
];

function useTypingDemo(isVisible: boolean) {
  const [step, setStep] = useState(0); // 0 = original, 1 = corrected
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!isVisible) return;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      setStep(1);
      return;
    }

    function cycle() {
      setStep((s) => {
        const next = s === 0 ? 1 : 0;
        timerRef.current = setTimeout(cycle, next === 1 ? 3500 : 2500);
        return next;
      });
    }

    timerRef.current = setTimeout(cycle, 2500);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isVisible]);

  return step;
}

function DemoCorrectedLine({ tokens }: { tokens: typeof DEMO_CORRECTED }) {
  return (
    <p className="landing-demo__text">
      {tokens.map((t, i) =>
        t.fixed ? (
          <mark key={i} className="landing-demo__fix">
            {t.text}
          </mark>
        ) : (
          <span key={i}>{t.text}</span>
        ),
      )}
    </p>
  );
}

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
}

export function LandingPage() {
  const videoRef = useScrollReveal();
  const statsRef = useScrollReveal();
  const featuresRef = useScrollReveal();
  const howRef = useScrollReveal();
  const demoRef = useScrollReveal();
  const storyRef = useScrollReveal();
  const ossRef = useScrollReveal();

  /* track demo visibility */
  const [demoVisible, setDemoVisible] = useState(false);
  const demoObserverRef = useCallback((el: HTMLDivElement | null) => {
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setDemoVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.3 },
    );
    observer.observe(el);
  }, []);

  const demoStep = useTypingDemo(demoVisible);

  return (
    <div className="landing">
      {/* ---- NAV ---- */}
      <nav className="landing-nav">
        <div className="landing-nav__inner">
          <div className="landing-nav__brand">
            <svg width="36" height="36" viewBox="0 0 40 40" fill="none" aria-hidden="true">
              <rect width="40" height="40" rx="10" fill="var(--accent)" />
              <text
                x="50%" y="54%"
                dominantBaseline="middle" textAnchor="middle"
                fill="white" fontSize="20" fontWeight="700"
              >
                D
              </text>
            </svg>
            <span className="landing-nav__name">DysLex AI</span>
          </div>
          <div className="landing-nav__links">
            <button className="landing-nav__link" onClick={() => scrollTo('features')}>Features</button>
            <button className="landing-nav__link" onClick={() => scrollTo('how-it-works')}>How it works</button>
            <button className="landing-nav__link" onClick={() => scrollTo('open-source')}>Open source</button>
          </div>
          <div className="landing-nav__actions">
            <Link to="/login" className="landing-btn landing-btn--ghost">Sign in</Link>
            <Link to="/signup" className="landing-btn landing-btn--primary">Get started</Link>
          </div>
        </div>
      </nav>

      {/* ---- HERO ---- */}
      <section className="landing-hero">
        <div className="landing-hero__inner landing-hero__inner--grid">
          {/* Left column */}
          <div className="landing-hero__content">
            <span className="landing-hero__badge anim anim-d1">
              Built by a dyslexic highschool student &middot; 47,000+ lines of code
            </span>
            <h1 className="landing-hero__title anim anim-d2">
              Your ideas are brilliant.{' '}
              <span className="landing-hero__accent">Now the world can read them.</span>
            </h1>
            <p className="landing-hero__subtitle anim anim-d3">
              An adaptive AI writing tool that learns how you think.
              No red squiggles. No judgment. No friction &mdash; just your
              ideas, finally on the page the way you meant them.
            </p>
            <div className="landing-hero__cta anim anim-d4">
              <Link to="/signup" className="landing-btn landing-btn--primary landing-btn--lg">
                Start writing free
              </Link>
              <button
                className="landing-btn landing-btn--ghost landing-btn--lg"
                onClick={() => scrollTo('video')}
                type="button"
              >
                Watch the demo
              </button>
            </div>
            <p className="landing-hero__note anim anim-d5">
              Open source &middot; No credit card &middot; No tracking
            </p>
          </div>

          {/* Right column — animated illustration */}
          <div className="landing-hero__visual anim anim-d3" aria-hidden="true">
            <svg viewBox="0 0 320 280" fill="none" className="landing-hero__svg">
              {/* Connecting dotted paths */}
              <path d="M80 70 L160 70" stroke="var(--accent)" strokeWidth="1.5" strokeDasharray="4 4" className="landing-hero__path" />
              <path d="M200 70 L260 120" stroke="var(--accent)" strokeWidth="1.5" strokeDasharray="4 4" className="landing-hero__path" />
              <path d="M260 160 L200 210" stroke="var(--accent)" strokeWidth="1.5" strokeDasharray="4 4" className="landing-hero__path" />

              {/* Stage 1: Microphone */}
              <g className="landing-hero__stage landing-hero__stage--1">
                <circle cx="50" cy="70" r="28" fill="var(--accent-l)" />
                <path d="M50 52a6 6 0 0 0-6 6v16a6 6 0 0 0 12 0V58a6 6 0 0 0-6-6z" fill="var(--accent)" />
                <path d="M38 70v4a12 12 0 0 0 24 0v-4" stroke="var(--accent)" strokeWidth="2" fill="none" />
                <line x1="50" y1="86" x2="50" y2="92" stroke="var(--accent)" strokeWidth="2" />
              </g>

              {/* Stage 2: Mind map */}
              <g className="landing-hero__stage landing-hero__stage--2">
                <circle cx="180" cy="55" r="10" fill="var(--accent)" opacity="0.8" />
                <circle cx="165" cy="80" r="7" fill="var(--accent)" opacity="0.5" />
                <circle cx="195" cy="78" r="8" fill="var(--accent)" opacity="0.6" />
                <line x1="180" y1="55" x2="165" y2="80" stroke="var(--accent)" strokeWidth="1.5" opacity="0.4" />
                <line x1="180" y1="55" x2="195" y2="78" stroke="var(--accent)" strokeWidth="1.5" opacity="0.4" />
              </g>

              {/* Stage 3: Document */}
              <g className="landing-hero__stage landing-hero__stage--3">
                <rect x="240" y="110" width="40" height="52" rx="4" fill="var(--accent-l)" stroke="var(--accent)" strokeWidth="1.5" />
                <line x1="250" y1="124" x2="270" y2="124" stroke="var(--accent)" strokeWidth="1.5" opacity="0.5" />
                <line x1="250" y1="132" x2="268" y2="132" stroke="var(--accent)" strokeWidth="1.5" opacity="0.5" />
                <line x1="250" y1="140" x2="265" y2="140" stroke="var(--accent)" strokeWidth="1.5" opacity="0.5" />
                <line x1="250" y1="148" x2="270" y2="148" stroke="var(--accent)" strokeWidth="1.5" opacity="0.5" />
              </g>

              {/* Stage 4: Checkmark */}
              <g className="landing-hero__stage landing-hero__stage--4">
                <circle cx="180" cy="210" r="28" fill="var(--accent)" opacity="0.12" />
                <circle cx="180" cy="210" r="18" fill="var(--accent)" />
                <polyline points="170,210 177,218 192,203" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </g>

              {/* Floating particles */}
              <circle cx="120" cy="130" r="3" fill="var(--accent)" opacity="0.3" className="landing-hero__particle landing-hero__particle--1" />
              <circle cx="220" cy="170" r="2" fill="var(--accent)" opacity="0.25" className="landing-hero__particle landing-hero__particle--2" />
              <circle cx="100" cy="200" r="2.5" fill="var(--accent)" opacity="0.2" className="landing-hero__particle landing-hero__particle--3" />
            </svg>
          </div>
        </div>
      </section>

      {/* ---- VIDEO ---- */}
      <section className="landing-video" id="video">
        <div className="landing-section__inner landing-reveal" ref={videoRef}>
          <h2 className="landing-section__title">See it in action</h2>
          <p className="landing-section__subtitle">
            Watch the 3-minute demo competing for a Golden Ticket from NVIDIA.
          </p>
          <div className="landing-video__embed">
            <iframe
              src="https://www.linkedin.com/embed/feed/update/urn:li:activity:7427011746856386560"
              frameBorder="0"
              allowFullScreen
              title="DysLex AI demo — NVIDIA Golden Ticket competition entry"
            />
          </div>
          <blockquote className="landing-video__quote">
            "The goal isn't to fix how someone writes — it's to free the ideas already inside them."
          </blockquote>
        </div>
      </section>

      {/* ---- STATS BAR ---- */}
      <section className="landing-stats-section">
        <div className="landing-stats landing-reveal" ref={statsRef}>
          <div className="landing-stats__item">
            <span className="landing-stats__number">1 in 5</span>
            <span className="landing-stats__label">people have dyslexia</span>
          </div>
          <div className="landing-stats__divider" aria-hidden="true" />
          <div className="landing-stats__item">
            <span className="landing-stats__number">47,000+</span>
            <span className="landing-stats__label">lines of code</span>
          </div>
          <div className="landing-stats__divider" aria-hidden="true" />
          <div className="landing-stats__item">
            <span className="landing-stats__number">327</span>
            <span className="landing-stats__label">likes on launch post</span>
          </div>
          <div className="landing-stats__divider" aria-hidden="true" />
          <div className="landing-stats__item">
            <span className="landing-stats__number">100%</span>
            <span className="landing-stats__label">open source</span>
          </div>
        </div>
      </section>

      {/* ---- FEATURES ---- */}
      <section className="landing-features" id="features">
        <div className="landing-section__inner landing-reveal" ref={featuresRef}>
          <h2 className="landing-section__title">Built for how you think</h2>
          <p className="landing-section__subtitle">
            Not another spell checker. A writing environment designed
            around the way your mind actually works.
          </p>

          <div className="landing-features__grid">
            {/* Voice */}
            <div className="landing-feature-card">
              <div className="landing-feature-card__icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                  <line x1="12" y1="19" x2="12" y2="23" />
                  <line x1="8" y1="23" x2="16" y2="23" />
                </svg>
              </div>
              <h3 className="landing-feature-card__title">Voice-first capture</h3>
              <p className="landing-feature-card__desc">
                Tap the mic and speak freely. Your ideas are transcribed
                in real-time and organized into thought cards you can rearrange.
              </p>
            </div>

            {/* Adaptive */}
            <div className="landing-feature-card">
              <div className="landing-feature-card__icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              </div>
              <h3 className="landing-feature-card__title">Adaptive AI</h3>
              <p className="landing-feature-card__desc">
                The more you write, the smarter it gets. DysLex AI learns
                your unique patterns and improves corrections over time &mdash;
                silently, in the background.
              </p>
            </div>

            {/* Modes */}
            <div className="landing-feature-card">
              <div className="landing-feature-card__icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <rect x="3" y="3" width="7" height="7" rx="1" />
                  <rect x="14" y="3" width="7" height="7" rx="1" />
                  <rect x="3" y="14" width="7" height="7" rx="1" />
                  <rect x="14" y="14" width="7" height="7" rx="1" />
                </svg>
              </div>
              <h3 className="landing-feature-card__title">Four writing modes</h3>
              <p className="landing-feature-card__desc">
                Capture ideas, map your thoughts, draft with guided structure,
                then polish with tracked suggestions. Each mode flows into the next.
              </p>
            </div>

            {/* Invisible */}
            <div className="landing-feature-card">
              <div className="landing-feature-card__icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </div>
              <h3 className="landing-feature-card__title">Invisible corrections</h3>
              <p className="landing-feature-card__desc">
                Never interrupted. Never corrected mid-thought. Fixes happen
                silently so you can focus on what matters: your ideas.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ---- HOW IT WORKS ---- */}
      <section className="landing-how" id="how-it-works">
        <div className="landing-section__inner landing-reveal" ref={howRef}>
          <h2 className="landing-section__title">How it works</h2>
          <div className="landing-how__steps">
            <div className="landing-how__step">
              <div className="landing-how__number">1</div>
              <h3>Capture</h3>
              <p>Speak or type your raw ideas. No structure needed &mdash; just get your thoughts out.</p>
            </div>
            <div className="landing-how__arrow" aria-hidden="true">
              <svg width="32" height="24" viewBox="0 0 32 24" fill="none">
                <path d="M0 12h28m0 0l-6-6m6 6l-6 6" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="landing-how__step">
              <div className="landing-how__number">2</div>
              <h3>Organize</h3>
              <p>Drag thought cards into a mind map. AI suggests connections and fills gaps.</p>
            </div>
            <div className="landing-how__arrow" aria-hidden="true">
              <svg width="32" height="24" viewBox="0 0 32 24" fill="none">
                <path d="M0 12h28m0 0l-6-6m6 6l-6 6" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="landing-how__step">
              <div className="landing-how__number">3</div>
              <h3>Write &amp; Polish</h3>
              <p>Draft with a guided scaffold. Polish with tracked changes and read-aloud support.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ---- LIVE DEMO ---- */}
      <section className="landing-demo-section">
        <div
          className="landing-section__inner landing-reveal"
          ref={(el) => { demoRef(el); demoObserverRef(el); }}
        >
          <h2 className="landing-section__title">See corrections in real time</h2>
          <p className="landing-section__subtitle">
            Watch how DysLex AI silently fixes errors without interrupting your flow.
          </p>

          <div className="landing-demo__window">
            <div className="landing-demo__titlebar">
              <span className="landing-demo__dot landing-demo__dot--red" />
              <span className="landing-demo__dot landing-demo__dot--yellow" />
              <span className="landing-demo__dot landing-demo__dot--green" />
              <span className="landing-demo__titlebar-text">DysLex AI — Draft Mode</span>
            </div>
            <div className="landing-demo__editor">
              {demoStep === 0 ? (
                <p className="landing-demo__text">
                  {DEMO_ORIGINAL.map((t, i) =>
                    t.err ? (
                      <span key={i} className="landing-demo__err">{t.text}</span>
                    ) : (
                      <span key={i}>{t.text}</span>
                    ),
                  )}
                </p>
              ) : (
                <DemoCorrectedLine tokens={DEMO_CORRECTED} />
              )}
            </div>
            <div className="landing-demo__status">
              <span className={`landing-demo__indicator ${demoStep === 1 ? 'landing-demo__indicator--done' : ''}`} />
              {demoStep === 0 ? 'Analyzing...' : '9 corrections applied silently'}
            </div>
          </div>
        </div>
      </section>

      {/* ---- STORY ---- */}
      <section className="landing-story-section">
        <div className="landing-section__inner landing-reveal" ref={storyRef}>
          <h2 className="landing-section__title">Built by someone who gets it</h2>
          <div className="landing-story">
            <p>
              DysLex AI was built by Connor, a dyslexic highschool student who spent
              years fighting tools that were designed to "fix" him. He wrote every one
              of the 47,000+ lines of code in this project, is competing for an NVIDIA
              Golden Ticket, and earned 327 likes on the launch post.
            </p>
            <p>
              This isn't a tool that was tested on dyslexic users.{' '}
              <strong>It was built by one, for the many.</strong> Every design decision &mdash; invisible
              corrections, voice-first input, positive framing &mdash; comes from lived experience.
            </p>
          </div>
        </div>
      </section>

      {/* ---- OPEN SOURCE + GITHUB ---- */}
      <section className="landing-oss" id="open-source">
        <div className="landing-section__inner landing-reveal" ref={ossRef}>
          <h2 className="landing-oss__title">Free and open source forever</h2>
          <p className="landing-oss__desc">
            DysLex AI is released under the Apache 2.0 license. Run it yourself,
            fork it, translate it, improve it. Powerful writing tools should be
            accessible to everyone.
          </p>

          <div className="landing-github__card">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
            </svg>
            <h3 className="landing-github__title">Get the code</h3>
            <p className="landing-github__desc">
              Clone the repo and run it locally in one command.
            </p>
            <div className="landing-github__cmd">
              <code>git clone https://github.com/DysLex-AI/DysLex.git && cd DysLex && python3 run.py --auto-setup</code>
            </div>
            <div className="landing-oss__actions">
              <Link to="/signup" className="landing-btn landing-btn--primary landing-btn--lg">
                Try it now
              </Link>
              <a
                href="https://github.com/DysLex-AI/DysLex"
                target="_blank"
                rel="noopener noreferrer"
                className="landing-btn landing-btn--ghost landing-btn--lg"
              >
                View on GitHub
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ---- FOOTER ---- */}
      <footer className="landing-footer">
        <div className="landing-footer__inner">
          <p className="landing-footer__copy">
            &copy; 2026 DysLex AI &middot; Apache 2.0 License &middot;{' '}
            <a
              href="https://github.com/DysLex-AI/DysLex"
              target="_blank"
              rel="noopener noreferrer"
              className="landing-footer__link"
            >
              GitHub
            </a>
          </p>
        </div>
      </footer>
    </div>
  );
}
