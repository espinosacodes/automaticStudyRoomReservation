import { motion } from 'motion/react'

export function Card({ children, className = '' }) {
  return (
    <div
      className={`rounded-2xl border border-hairline bg-white p-6 shadow-sm ${className}`}
    >
      {children}
    </div>
  )
}

export function Section({ children, className = '' }) {
  return <section className={`mx-auto w-full max-w-3xl px-5 ${className}`}>{children}</section>
}

export function Eyebrow({ children }) {
  return (
    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">{children}</p>
  )
}

export function Reveal({ children, delay = 0, className = '' }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 0.4, ease: 'easeOut', delay }}
      className={className}
    >
      {children}
    </motion.div>
  )
}
