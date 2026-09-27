import { useEffect, useState } from 'react'
import { BookOpen, ShieldCheck, ArrowRight } from 'lucide-react'

import { Atmosphere, useReducedMotion } from './Atmosphere.jsx'
import { GlassOptics } from './GlassOptics.jsx'
import { Sidebar } from './Sidebar.jsx'

export function AuthGate({ children }) {
  const [session, setSession] = useState(null)
  const [error, setError] = useState(false)
  const reducedMotion = useReducedMotion()

  useEffect(() => {
    fetch('/auth/session', { cache: 'no-store' })
      .then((response) => {
        if (!response.ok) throw new Error('Session unavailable')
        return response.json()
      })
      .then(setSession)
      .catch(() => setError(true))
  }, [])

  const logout = async () => {
    const response = await fetch('/auth/logout', { method: 'POST' })
    if (response.ok) window.location.assign('/')
    else setError(true)
  }

  if (session?.user) {
    return (
      <>
        <Atmosphere reducedMotion={reducedMotion} />
        <GlassOptics enabled reducedMotion={reducedMotion} />
        <div className="shell">
          <Sidebar user={session.user} onLogout={logout} />
          <main className="shell-main">
            {error && (
              <p role="alert" className="notice">
                Sign out failed. Please try again.
              </p>
            )}
            {children}
          </main>
        </div>
      </>
    )
  }

  const reason = new URLSearchParams(window.location.search).get('auth_error')
  return (
    <>
      <Atmosphere reducedMotion={reducedMotion} />
      <GlassOptics enabled reducedMotion={reducedMotion} />
      <div className="login-shell">
        <main className="login-page">
        <section className="login-card" data-optical>
          <div className="login-card-body">
            <div className="login-icon">
              <BookOpen size={30} />
            </div>
            <p className="eyebrow">Valance workspace</p>
            <h1>
              Your room.
              <br />
              <em>Your workday.</em>
            </h1>
            <p className="login-description">
              Reservations, schedules, and official confirmations for the ICESI study rooms. All in
              one place.
            </p>
            {error ? (
              <p role="alert">
                Sign-in is temporarily unavailable.{' '}
                <button className="button ghost" onClick={() => window.location.reload()}>
                  Retry
                </button>
              </p>
            ) : !session ? (
              <p role="status">Checking your session...</p>
            ) : !session.configured ? (
              <p role="status">Google sign-in is being configured. Reservations remain private.</p>
            ) : (
              <a className="button google-signin" href="/auth/google">
                <span className="google-letter" aria-hidden="true">
                  G
                </span>
                Continue with Google <ArrowRight size={17} />
              </a>
            )}
            {reason && (
              <p className="login-error" role="alert">
                {reason === 'denied'
                  ? 'This Google account is not on the Valance access list. Choose an approved email.'
                  : 'Sign-in could not be completed. Please try again.'}
              </p>
            )}
            <div className="login-note">
              <ShieldCheck size={17} />
              <span>Access is limited to approved Valance email addresses.</span>
            </div>
          </div>
        </section>
        <p className="login-footnote">Study rooms · Monday to Friday · 08:00 to 20:00</p>
      </main>
      </div>
    </>
  )
}
