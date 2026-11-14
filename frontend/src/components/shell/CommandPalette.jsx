// Ctrl/Cmd+K command palette: jump to any module or to a section of the Home page.
import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useLocation, useNavigate } from 'react-router-dom'
import Icon from '../Icon.jsx'
import ShellIcon from './ShellIcons.jsx'
import { PALETTE_ITEMS, filterItems } from './paletteItems.js'

export default function CommandPalette({ onClose }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const input = useRef(null)
  const opener = useRef(typeof document !== 'undefined' ? document.activeElement : null)
  const listId = useId()
  const results = useMemo(() => filterItems(PALETTE_ITEMS, query), [query])

  useEffect(() => {
    input.current?.focus()
    const previous = opener.current
    return () => { if (previous && typeof previous.focus === 'function' && document.contains(previous)) previous.focus() }
  }, [])
  useEffect(() => { setActive(0) }, [query])

  function choose(item) {
    onClose()
    if (!item) return
    if (item.section) {
      // Home loads its market sections lazily, so it handles the scrolling itself.
      if (pathname === '/') window.dispatchEvent(new CustomEvent('careernova:scroll-to', { detail: item.section }))
      else navigate('/', { state: { scrollTo: item.section } })
    } else if (item.to !== pathname) navigate(item.to)
  }

  function onKeyDown(event) {
    if (event.key === 'Escape') { event.preventDefault(); onClose() }
    else if (event.key === 'ArrowDown') { event.preventDefault(); setActive(i => Math.min(i + 1, results.length - 1)) }
    else if (event.key === 'ArrowUp') { event.preventDefault(); setActive(i => Math.max(i - 1, 0)) }
    else if (event.key === 'Enter') { event.preventDefault(); choose(results[active]) }
    else if (event.key === 'Tab') event.preventDefault() // the search box is the only control, so focus stays in the dialog
  }

  let lastGroup = null
  return createPortal(<div className="cmdk-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <div className="cmdk" role="dialog" aria-modal="true" aria-label="Search CareerNova" onKeyDown={onKeyDown}>
      <div className="cmdk-input">
        <ShellIcon name="search" />
        <input ref={input} value={query} onChange={event => setQuery(event.target.value)} placeholder="Jump to a module or section…"
          role="combobox" aria-expanded="true" aria-controls={listId} aria-autocomplete="list"
          aria-activedescendant={results[active] ? `${listId}-${results[active].id}` : undefined} aria-label="Search modules and sections" />
        <kbd>Esc</kbd>
      </div>
      <ul id={listId} role="listbox" className="cmdk-list" aria-label="Results">
        {results.length === 0 && <li className="cmdk-empty" role="presentation">No module or section matches “{query}”.</li>}
        {results.flatMap((item, index) => {
          const heading = item.group !== lastGroup ? item.group : null
          lastGroup = item.group
          return [heading && <li key={`group-${heading}`} className="cmdk-group" role="presentation">{heading}</li>,
            <li key={item.id} id={`${listId}-${item.id}`} role="option" aria-selected={index === active}
              className={index === active ? 'is-active' : ''} onMouseEnter={() => setActive(index)}
              onMouseDown={event => event.preventDefault()} onClick={() => choose(item)}>
              <span className="cmdk-icon"><Icon name={item.icon} size={16} /></span>
              <span className="cmdk-text"><strong>{item.label}</strong><small>{item.hint}</small></span>
              {index === active && <span className="cmdk-enter" aria-hidden="true"><ShellIcon name="enter" size={14} /></span>}
            </li>].filter(Boolean)
        })}
      </ul>
    </div>
  </div>, document.body)
}
