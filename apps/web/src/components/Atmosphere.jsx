/**
 * Page atmosphere: a slowly drifting mesh gradient that the liquid glass
 * refracts. Kept as a separate visual layer so semantic text stays crisp and
 * selectable above it. Disabled when the visitor asks for reduced motion.
 */
import { useEffect, useState } from 'react'
import { MeshGradient } from '@paper-design/shaders-react'

const COLORS = ['#fffbf5', '#f7f2e9', '#f8cfa4', '#f6821f', '#7fb3e8', '#e3d9c9']

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

function usePageVisible() {
  const [visible, setVisible] = useState(!document.hidden)
  useEffect(() => {
    const update = () => setVisible(!document.hidden)
    document.addEventListener('visibilitychange', update)
    return () => document.removeEventListener('visibilitychange', update)
  }, [])
  return visible
}

export function Atmosphere({ reducedMotion }) {
  const visible = usePageVisible()
  return (
    <div className="atmosphere" aria-hidden="true">
      <MeshGradient
        className="liquid-field"
        colors={COLORS}
        speed={reducedMotion || !visible ? 0 : 0.12}
        distortion={0.8}
        swirl={0.62}
        grainMixer={0}
        grainOverlay={0}
        frame={62000}
        minPixelRatio={1}
        maxPixelCount={1000000}
        webGlContextAttributes={{ alpha: true, preserveDrawingBuffer: true, powerPreference: 'low-power' }}
      />
      <div className="atmosphere-wash" />
    </div>
  )
}
