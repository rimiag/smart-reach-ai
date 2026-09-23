'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Link from 'next/link';
import Logo from '@/components/Logo';

/* ------------------------------------------------------------------ */
/* Illustrative dashboard mockup data (pure CSS, no image assets)      */
/* ------------------------------------------------------------------ */

const MOCK_SIDEBAR = ['Dashboard', 'Campaigns', 'Leads', 'Replies', 'Analytics'];

const MOCK_STATS = [
  {
    label: 'Active campaigns',
    value: '12',
    delta: '+3 this week',
    deltaCls: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  },
  {
    label: 'Qualified leads',
    value: '1,284',
    delta: '+18%',
    deltaCls: 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  },
  {
    label: 'Replies detected',
    value: '316',
    delta: '+9%',
    deltaCls: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  },
];

// Full literal height classes so Tailwind's scanner picks them up.
const MOCK_BARS = [
  'h-[40%]', 'h-[55%]', 'h-[45%]', 'h-[70%]', 'h-[62%]', 'h-[80%]',
  'h-[58%]', 'h-[90%]', 'h-[74%]', 'h-[96%]', 'h-[84%]', 'h-full',
];

const MOCK_LEADS = [
  {
    domain: 'acmehealth.com',
    status: 'Qualified',
    pillCls: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
    dotCls: 'bg-green-500',
  },
  {
    domain: 'medtechsolutions.io',
    status: 'Contacted',
    pillCls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    dotCls: 'bg-blue-500',
  },
  {
    domain: 'brightlabs.co',
    status: 'New',
    pillCls: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
    dotCls: 'bg-gray-400',
  },
  {
    domain: 'novacareclinic.com',
    status: 'Replied',
    pillCls: 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300',
    dotCls: 'bg-purple-500',
  },
];

/* ------------------------------------------------------------------ */
/* Content data                                                        */
/* ------------------------------------------------------------------ */

const STEPS = [
  {
    step: '1',
    title: 'Discover',
    copy: 'Run targeted web searches across your keywords and locations to surface companies that fit your ideal customer profile.',
    iconColor: 'text-blue-600 dark:text-blue-400',
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
      />
    ),
  },
  {
    step: '2',
    title: 'Qualify',
    copy: 'AI researches every site it finds, scores the fit, and enriches your pipeline so you only chase leads worth your time.',
    iconColor: 'text-green-600 dark:text-green-400',
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    ),
  },
  {
    step: '3',
    title: 'Outreach',
    copy: 'Generate a personalized email for each lead, approve it in one click, and track replies as they come in.',
    iconColor: 'text-purple-600 dark:text-purple-400',
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
      />
    ),
  },
];

const FEATURES = [
  {
    title: 'Web-scale discovery',
    copy: 'Keyword and location-aware searches surface companies that match your ideal customer profile.',
    iconBg: 'bg-blue-100 dark:bg-blue-900/40',
    iconColor: 'text-blue-600 dark:text-blue-400',
    icon: (
      <>
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.6 9h16.8M3.6 15h16.8M12 3a15 15 0 010 18M12 3a15 15 0 000 18" />
      </>
    ),
  },
  {
    title: 'AI lead qualification',
    copy: 'Every discovered site is researched and scored automatically, so your pipeline holds only worthwhile leads.',
    iconBg: 'bg-green-100 dark:bg-green-900/40',
    iconColor: 'text-green-600 dark:text-green-400',
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    ),
  },
  {
    title: 'Personalized drafting',
    copy: 'Emails are written for each lead — their site, their context — never a generic blast.',
    iconBg: 'bg-purple-100 dark:bg-purple-900/40',
    iconColor: 'text-purple-600 dark:text-purple-400',
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
      />
    ),
  },
  {
    title: 'Human-approved sending',
    copy: 'Nothing leaves without your sign-off. Review, edit and approve every message before it ships.',
    iconBg: 'bg-indigo-100 dark:bg-indigo-900/40',
    iconColor: 'text-indigo-600 dark:text-indigo-400',
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
      />
    ),
  },
  {
    title: 'Reply detection',
    copy: 'Inbox monitoring spots replies automatically, so you can follow up at exactly the right moment.',
    iconBg: 'bg-rose-100 dark:bg-rose-900/40',
    iconColor: 'text-rose-600 dark:text-rose-400',
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
      />
    ),
  },
  {
    title: 'Real-time analytics',
    copy: 'Campaign, lead and reply metrics in one dashboard to steer every outreach decision.',
    iconBg: 'bg-amber-100 dark:bg-amber-900/40',
    iconColor: 'text-amber-600 dark:text-amber-400',
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
      />
    ),
  },
];

const PROOF_POINTS = ['Human-approved sending', 'AI reply detection', 'Built-in analytics'];

const USE_CASES = [
  {
    title: 'Sales teams',
    copy: 'Keep a steady flow of qualified prospects moving — without manual prospecting.',
    iconBg: 'bg-teal-100 dark:bg-teal-900/40',
    iconColor: 'text-teal-600 dark:text-teal-400',
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-8.995-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
      />
    ),
  },
  {
    title: 'Marketing agencies',
    copy: 'Run outreach programs for multiple clients from one shared workspace.',
    iconBg: 'bg-sky-100 dark:bg-sky-900/40',
    iconColor: 'text-sky-600 dark:text-sky-400',
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
      />
    ),
  },
  {
    title: 'B2B service providers',
    copy: 'Find companies that need exactly what you offer — and reach them first.',
    iconBg: 'bg-orange-100 dark:bg-orange-900/40',
    iconColor: 'text-orange-600 dark:text-orange-400',
    icon: (
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
      />
    ),
  },
  {
    title: 'Founders & lean teams',
    copy: 'Prospect like a full SDR team — without hiring one.',
    iconBg: 'bg-violet-100 dark:bg-violet-900/40',
    iconColor: 'text-violet-600 dark:text-violet-400',
    icon: (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    ),
  },
];

const FAQS = [
  {
    q: 'Where do the leads come from?',
    a: 'ReachPulse runs targeted web searches across the keywords and locations you define, using professional search APIs. Every lead is a real company website — no scraped contact lists.',
  },
  {
    q: 'Will it email people without my approval?',
    a: 'No. Every email is drafted for your review. Nothing is sent until you explicitly approve it.',
  },
  {
    q: 'Can I find more leads for an existing campaign?',
    a: 'Yes. Run research again on any campaign and ReachPulse searches deeper, adding only new websites and skipping everything you already have.',
  },
  {
    q: 'What do I need to get started?',
    a: 'Create an account, describe your ideal customer with keywords and locations, and launch your first campaign. Sending and reply detection use the inbox configured by your administrator.',
  },
];

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function HomePage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  // Signed-in users go straight to their dashboard
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace('/dashboard');
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
        <div className="text-gray-600 dark:text-gray-300">Loading...</div>
      </main>
    );
  }

  return (
    <main className="relative flex min-h-screen flex-col overflow-x-clip bg-gradient-to-br from-blue-50 via-indigo-50 to-indigo-100 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800">
      {/* Navbar */}
      <header className="sticky top-0 z-10 border-b border-white/60 bg-white/70 backdrop-blur dark:border-gray-800 dark:bg-gray-900/70">
        <div className="container flex h-16 items-center justify-between">
          <Logo />
          <nav className="hidden items-center gap-8 text-sm font-medium text-gray-600 dark:text-gray-300 md:flex">
            <a href="#how-it-works" className="transition-colors hover:text-indigo-600 dark:hover:text-indigo-400">
              How it works
            </a>
            <a href="#features" className="transition-colors hover:text-indigo-600 dark:hover:text-indigo-400">
              Features
            </a>
          </nav>
          <nav className="flex items-center gap-3">
            {isAuthenticated ? (
              <Link
                href="/dashboard"
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700"
              >
                Go to dashboard
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className="rounded-lg px-4 py-2 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-800"
                >
                  Sign in
                </Link>
                <Link
                  href="/register"
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700"
                >
                  Get started
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="container relative pt-16 text-center sm:pt-20">
        <div
          aria-hidden
          className="pointer-events-none absolute left-1/2 top-0 -z-10 h-72 w-[46rem] max-w-none -translate-x-1/2 rounded-full bg-indigo-300/30 blur-3xl dark:bg-indigo-600/20"
        />
        <div className="mx-auto max-w-3xl">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-white/70 px-3 py-1 text-xs font-medium text-indigo-700 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-300">
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            by Smart Reach AI
          </span>

          <h1 className="mt-6 text-5xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-6xl">
            <span className="bg-gradient-to-r from-indigo-600 via-blue-600 to-blue-500 bg-clip-text text-transparent dark:from-indigo-400 dark:to-blue-300">
              ReachPulse
            </span>
          </h1>

          <p className="mt-4 text-2xl font-semibold text-gray-900 dark:text-white sm:text-3xl">
            Turn web searches into qualified leads and real conversations.
          </p>

          <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-gray-600 dark:text-gray-300 sm:text-lg">
            ReachPulse finds companies that match your ideal customer, researches and qualifies
            them with AI, and drafts personalized outreach — you stay in control of every email
            that goes out.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            {isAuthenticated ? (
              <Link
                href="/dashboard"
                className="rounded-lg bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700"
              >
                Open dashboard
              </Link>
            ) : (
              <>
                <Link
                  href="/register"
                  className="rounded-lg bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-700"
                >
                  Start free
                </Link>
                <Link
                  href="/login"
                  className="rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-semibold text-gray-700 shadow-sm transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
                >
                  Sign in
                </Link>
              </>
            )}
          </div>

          <ul className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-gray-600 dark:text-gray-400">
            {PROOF_POINTS.map((item) => (
              <li key={item} className="flex items-center gap-1.5">
                <svg className="h-4 w-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Product mockup */}
      <section className="container mt-14 sm:mt-16">
        <div className="relative mx-auto max-w-5xl">
          <div
            aria-hidden
            className="absolute -inset-x-8 -top-6 bottom-6 rounded-[2rem] bg-gradient-to-r from-indigo-500/20 via-blue-500/20 to-purple-500/20 blur-2xl"
          />
          <div className="relative overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl dark:border-gray-800 dark:bg-gray-900">
            {/* browser chrome */}
            <div className="flex items-center gap-2 border-b border-gray-100 bg-gray-50 px-4 py-3 dark:border-gray-800 dark:bg-gray-800/60">
              <span className="h-3 w-3 rounded-full bg-red-400" />
              <span className="h-3 w-3 rounded-full bg-amber-400" />
              <span className="h-3 w-3 rounded-full bg-green-400" />
              <span className="ml-3 hidden rounded-md bg-white px-3 py-1 text-xs text-gray-500 ring-1 ring-gray-200 dark:bg-gray-900 dark:text-gray-400 dark:ring-gray-700 sm:block">
                reachpulse.medidatalab.com/dashboard
              </span>
            </div>
            <div className="flex">
              {/* mini sidebar */}
              <div className="hidden w-44 shrink-0 space-y-1 border-r border-gray-100 p-4 dark:border-gray-800 sm:block">
                {MOCK_SIDEBAR.map((item, i) => (
                  <div
                    key={item}
                    className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium ${
                      i === 0
                        ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300'
                        : 'text-gray-500 dark:text-gray-400'
                    }`}
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full ${
                        i === 0 ? 'bg-indigo-500' : 'bg-gray-300 dark:bg-gray-600'
                      }`}
                    />
                    {item}
                  </div>
                ))}
              </div>
              {/* main panel */}
              <div className="flex-1 space-y-4 p-5 text-left">
                <div className="grid gap-3 sm:grid-cols-3">
                  {MOCK_STATS.map(({ label, value, delta, deltaCls }) => (
                    <div key={label} className="rounded-xl border border-gray-100 p-4 dark:border-gray-800">
                      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
                      <div className="mt-1 flex items-center justify-between gap-2">
                        <span className="text-2xl font-bold text-gray-900 dark:text-white">{value}</span>
                        <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${deltaCls}`}>
                          {delta}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="rounded-xl border border-gray-100 p-4 dark:border-gray-800">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                      Leads discovered
                    </span>
                    <span className="text-xs text-gray-400 dark:text-gray-500">Last 12 weeks</span>
                  </div>
                  <div className="flex h-24 items-end gap-1.5">
                    {MOCK_BARS.map((h, i) => (
                      <div
                        key={i}
                        className={`flex-1 rounded-t bg-gradient-to-t from-indigo-500 to-blue-400 ${h}`}
                      />
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  {MOCK_LEADS.map(({ domain, status, pillCls, dotCls }) => (
                    <div
                      key={domain}
                      className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-2.5 dark:border-gray-800"
                    >
                      <span className="flex items-center gap-2.5 text-xs font-medium text-gray-700 dark:text-gray-200">
                        <span className={`h-2 w-2 rounded-full ${dotCls}`} />
                        {domain}
                      </span>
                      <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${pillCls}`}>
                        {status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="container scroll-mt-20 pt-20 sm:pt-24">
        <div className="mb-12 text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
            How it works
          </p>
          <h2 className="mt-2 text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
            From first search to sent email — one pipeline
          </h2>
        </div>
        <div className="relative grid gap-8 md:grid-cols-3 md:gap-6">
          {/* connector line (desktop) */}
          <div
            aria-hidden
            className="absolute left-[16%] right-[16%] top-8 hidden border-t-2 border-dashed border-indigo-200 dark:border-indigo-500/30 md:block"
          />
          {STEPS.map(({ step, title, copy, iconColor, icon }) => (
            <div key={step} className="relative text-center">
              <div className="relative z-10 mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-white shadow-md dark:bg-gray-800">
                <svg className={`h-8 w-8 ${iconColor}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {icon}
                </svg>
                <span className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
                  {step}
                </span>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
              <p className="mx-auto mt-2 max-w-xs text-sm leading-6 text-gray-600 dark:text-gray-400">
                {copy}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <div className="mt-20 border-y border-gray-100 bg-white/70 dark:border-gray-800 dark:bg-gray-900/60 sm:mt-24">
        <section id="features" className="container scroll-mt-20 py-16 sm:py-20">
        <div className="mb-12 text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
            Features
          </p>
          <h2 className="mt-2 text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
            Everything you need, end to end
          </h2>
        </div>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ title, copy, iconBg, iconColor, icon }) => (
            <div
              key={title}
              className="rounded-xl border border-white/60 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-gray-800"
            >
              <div className={`mb-4 inline-flex h-11 w-11 items-center justify-center rounded-lg ${iconBg}`}>
                <svg className={`h-6 w-6 ${iconColor}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {icon}
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-gray-600 dark:text-gray-400">{copy}</p>
            </div>
          ))}
        </div>
        </section>
      </div>

      {/* Who it's for */}
      <section className="container pt-20 sm:pt-24">
        <div className="mb-12 text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
            Who it&apos;s for
          </p>
          <h2 className="mt-2 text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
            Built for teams that live on outreach
          </h2>
        </div>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {USE_CASES.map(({ title, copy, iconBg, iconColor, icon }) => (
            <div
              key={title}
              className="rounded-xl border border-white/60 bg-white/80 p-5 text-left shadow-sm transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-gray-800/80"
            >
              <div className={`mb-3 inline-flex h-10 w-10 items-center justify-center rounded-lg ${iconBg}`}>
                <svg className={`h-5 w-5 ${iconColor}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {icon}
                </svg>
              </div>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">{title}</h3>
              <p className="mt-1.5 text-sm leading-6 text-gray-600 dark:text-gray-400">{copy}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="container pt-20 sm:pt-24">
        <div className="mb-12 text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
            FAQ
          </p>
          <h2 className="mt-2 text-3xl font-bold tracking-tight text-gray-900 dark:text-white">
            Frequently asked questions
          </h2>
        </div>
        <div className="mx-auto max-w-3xl space-y-3">
          {FAQS.map(({ q, a }) => (
            <details
              key={q}
              className="group rounded-xl border border-white/60 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-800"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-left text-sm font-semibold text-gray-900 dark:text-white [&::-webkit-details-marker]:hidden">
                {q}
                <svg
                  className="h-5 w-5 shrink-0 text-gray-400 transition-transform group-open:rotate-180"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </summary>
              <p className="mt-3 text-sm leading-6 text-gray-600 dark:text-gray-400">{a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* CTA band */}
      <section className="container pt-20 sm:pt-24">
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-600 to-blue-600 px-6 py-12 text-center shadow-lg sm:px-12">
          <h2 className="text-2xl font-bold text-white sm:text-3xl">Ready to fill your pipeline?</h2>
          <p className="mx-auto mt-2 max-w-xl text-indigo-100">
            Create your first campaign in minutes — discover, qualify and reach your next
            customers today.
          </p>
          <div className="mt-6">
            {isAuthenticated ? (
              <Link
                href="/dashboard"
                className="inline-block rounded-lg bg-white px-6 py-3 text-sm font-semibold text-indigo-700 shadow-sm transition-colors hover:bg-indigo-50"
              >
                Open dashboard
              </Link>
            ) : (
              <Link
                href="/register"
                className="inline-block rounded-lg bg-white px-6 py-3 text-sm font-semibold text-indigo-700 shadow-sm transition-colors hover:bg-indigo-50"
              >
                Start free
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-16 border-t border-white/60 bg-white/50 dark:border-gray-800 dark:bg-gray-900/50">
        <div className="container flex flex-col items-center justify-between gap-4 py-6 sm:flex-row">
          <div className="flex items-center gap-3">
            <Logo />
            <span className="hidden text-sm text-gray-500 dark:text-gray-400 sm:inline">
              Discover. Engage. Convert.
            </span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className="text-gray-500 dark:text-gray-400">
              © 2026 Smart Reach AI · ReachPulse
            </span>
            {!isAuthenticated && (
              <>
                <Link
                  href="/login"
                  className="font-medium text-gray-700 transition-colors hover:text-indigo-600 dark:text-gray-200 dark:hover:text-indigo-400"
                >
                  Sign in
                </Link>
                <Link
                  href="/register"
                  className="font-medium text-indigo-600 transition-colors hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
                >
                  Get started
                </Link>
              </>
            )}
          </div>
        </div>
      </footer>
    </main>
  );
}
