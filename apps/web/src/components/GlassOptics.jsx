/**
 * Liquid glass optics.
 *
 * The refraction is a real WebGL pass over the drifting mesh gradient, applied
 * to inert plates positioned exactly over the elements marked `data-optical`.
 * Semantic content (text, links, buttons) stays in the DOM above the optical
 * layer, which is the rule that keeps the page readable and selectable instead
 * of turning into one big shader.
 *
 * If WebGL is unavailable the plates are dropped and the elements keep their
 * frosted CSS surface, so the page degrades instead of breaking.
 */
import { useEffect, useRef, useState } from 'react'
import { LiquidGlass } from '@ybouane/liquidglass'

const DEFAULTS = {
  blurAmount: 0.14,
  refraction: 0.7,
  chromAberration: 0.03,
  edgeHighlight: 0.14,
  specular: 0.18,
  fresnel: 0.5,
  distortion: 0.05,
  shadowOpacity: 0.05,
  shadowSpread: 10,
  shadowOffsetY: 5,
  brightness: 0.1,
  saturation: 0.05,
  tintStrength: 0.02,
}

export function GlassOptics({ reducedMotion, enabled }) {
  const rootRef = useRef(null)
  const [revision, setRevision] = useState(0)

  // The dashboard mounts its cards only after the status fetch resolves, so the
  // set of optical targets changes after this component first runs. Rebuild the
  // optics whenever the count changes, otherwise late panels get no glass.
  useEffect(() => {
    if (!enabled) return undefined
    let count = document.querySelectorAll('[data-optical]').length
    const observer = new MutationObserver(() => {
      const next = document.querySelectorAll('[data-optical]').length
      if (next !== count) {
        count = next
        setRevision((value) => value + 1)
      }
    })
    observer.observe(document.body, { childList: true, subtree: true })
    return () => observer.disconnect()
  }, [enabled])

  useEffect(() => {
    if (!enabled) return undefined
    const root = rootRef.current
    if (!root) return undefined

    let active = true
    let instance
    let frame
    let previous = 0
    let dirty = true

    const source = document.createElement('canvas')
    source.className = 'optical-source'
    source.setAttribute('aria-hidden', 'true')
    root.append(source)
    const context = source.getContext('2d')

    const controls = Array.from(document.querySelectorAll('[data-optical]'))
    const plates = controls.map(() => {
      const plate = document.createElement('div')
      plate.className = 'optical-plate'
      plate.setAttribute('aria-hidden', 'true')
      root.append(plate)
      return plate
    })
    if (controls.length === 0) return undefined

    function sync() {
      const width = window.innerWidth
      const height = window.innerHeight
      if (source.width !== width || source.height !== height) {
        source.width = width
        source.height = height
      }
      controls.forEach((control, index) => {
        const rect = control.getBoundingClientRect()
        const plate = plates[index]
        const pinned = rect.bottom < 0 || rect.top > height || rect.width === 0
        plate.style.left = `${pinned ? -5000 : rect.left}px`
        plate.style.top = `${rect.top}px`
        plate.style.width = `${Math.max(1, rect.width)}px`
        plate.style.height = `${Math.max(1, rect.height)}px`
        const radius = parseFloat(getComputedStyle(control).borderRadius) || 22
        const config = JSON.stringify({ cornerRadius: radius, zRadius: 16 })
        if (plate.dataset.config !== config) plate.dataset.config = config
      })

      if (!context) return
      context.clearRect(0, 0, width, height)
      context.fillStyle = '#fffbf5'
      context.fillRect(0, 0, width, height)
      const mesh = document.querySelector('.atmosphere canvas')
      if (mesh?.width && mesh?.height) {
        const rect = mesh.getBoundingClientRect()
        context.globalAlpha = 0.85
        context.drawImage(mesh, rect.left, rect.top, rect.width, rect.height)
        context.globalAlpha = 1
      }
      instance?.markChanged()
    }

    function tick(time) {
      if (!active) return
      // Refresh on interaction, with a slow heartbeat for the drifting mesh.
      const stale = dirty && time - previous > 80
      const heartbeat = !reducedMotion && time - previous > 500
      if (!document.hidden && (stale || heartbeat)) {
        sync()
        previous = time
        dirty = false
      }
      frame = requestAnimationFrame(tick)
    }

    const invalidate = () => {
      dirty = true
    }
    const observer = new ResizeObserver(invalidate)
    controls.forEach((control) => observer.observe(control))
    window.addEventListener('resize', invalidate)
    window.addEventListener('pointermove', invalidate, { passive: true })
    window.addEventListener('wheel', invalidate, { passive: true })
    window.addEventListener('pointerdown', invalidate, { passive: true })
    window.addEventListener('scroll', invalidate, { capture: true, passive: true })

    sync()
    LiquidGlass.init({ root, glassElements: plates, defaults: DEFAULTS })
      .then((result) => {
        if (!active) {
          result.destroy()
          return
        }
        instance = result
        root.dataset.ready = 'true'
        frame = requestAnimationFrame(tick)
      })
      .catch(() => {
        // WebGL unavailable: drop the plates, keep the CSS frosted surfaces.
        root.replaceChildren()
      })

    return () => {
      active = false
      cancelAnimationFrame(frame)
      observer.disconnect()
      window.removeEventListener('resize', invalidate)
      window.removeEventListener('pointermove', invalidate)
      window.removeEventListener('wheel', invalidate)
      window.removeEventListener('pointerdown', invalidate)
      window.removeEventListener('scroll', invalidate, true)
      instance?.destroy()
      root.replaceChildren()
    }
  }, [enabled, reducedMotion, revision])

  return <div className="optical-layer" ref={rootRef} aria-hidden="true" />
}
