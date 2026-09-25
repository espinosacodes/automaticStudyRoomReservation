import { motion } from 'motion/react'

/**
 * One subtle entrance, used sparingly. The page is a utility view, so motion
 * stays minimal and respects the visitor's reduced-motion preference.
 */
export function Reveal({ children, delay = 0, className = '' }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.35, ease: 'easeOut', delay }}
      className={className}
    >
      {children}
    </motion.div>
  )
}
