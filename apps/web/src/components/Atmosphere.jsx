/**
 * Page atmosphere: a slowly drifting warm gradient that sits behind the
 * frosted glass surfaces. Pure CSS, no WebGL dependency, so the status page
 * builds offline and stays inside the Cloudflare palette (warm paper,
 * orange, dot grid). Disabled when the visitor asks for reduced motion.
 */
import { useEffect, useState } from 'react'

export function useReducedMotion() {
  const [reduced, setReduced] = useState(
    () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false,
  )
  useEffect(() => {
    const query = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    if (!query) return undefined
    const update = () => setReduced(query.matches)
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [])
  return reduced
}

export function Atmosphere({ reducedMotion }) {
  return (
    <div className="atmosphere" aria-hidden="true">
      <div
        className={reducedMotion ? 'liquid-field is-still' : 'liquid-field'}
      />
      <div className="atmosphere-wash" />
    </div>
  )
}
