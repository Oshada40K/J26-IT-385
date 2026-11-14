// Renders its children only when the area comes near the viewport. Until then a placeholder of
// the same height holds the space, so nothing below jumps when the content arrives.
import { Suspense, useEffect, useRef, useState } from 'react'
import { watchViewport } from './viewport.js'

export default function LazySection({ id, minHeight, fallback, children, margin = 400 }) {
  const ref = useRef(null)
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    if (visible || !ref.current) return undefined
    return watchViewport(ref.current, { margin }, inView => { if (inView) setVisible(true) })
  }, [visible, margin])
  return <div id={id} ref={ref} className="lazy-section" style={visible ? undefined : { minHeight }}>
    {visible ? <Suspense fallback={fallback}>{children}</Suspense> : fallback}
  </div>
}
