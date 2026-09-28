/**
 * Liquid glass optics (CSS-only fallback).
 *
 * The frosted surfaces in styles.css (backdrop-filter blur plus translucent
 * backgrounds) already give the glass read. The previous WebGL refraction
 * pass is intentionally not loaded here so the status page builds with zero
 * extra dependencies and works where WebGL is unavailable. The component
 * stays as a no-op so callers do not need to change.
 */
export function GlassOptics() {
  return null
}
