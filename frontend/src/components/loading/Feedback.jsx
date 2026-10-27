// Small loading feedback pieces: reload button, inline spinner and retryable error card.
import Icon from '../Icon.jsx'
import './loading.css'

export function Spinner({ className = '' }) {
  return <span className={`fx-spinner ${className}`} aria-hidden="true" />
}

// The refresh icon turns on hover and spins while `loading`; the label switches to `loadingLabel`.
export function ReloadButton({ onClick, loading = false, disabled = false, label = 'Refresh', loadingLabel = 'Refreshing…', tone = 'secondary', className = '' }) {
  return <button type="button" className={`reload-button ${tone === 'secondary' ? 'button-secondary' : ''} ${loading ? 'is-loading' : ''} ${className}`}
    onClick={onClick} disabled={loading || disabled} aria-busy={loading || undefined}>
    <span className="reload-icon"><Icon name="refresh" size={16} /></span>
    <span>{loading ? loadingLabel : label}</span>
  </button>
}

export function ErrorState({ title = 'We could not load this', message, onRetry, retrying = false, retryLabel = 'Try again', children, className = '' }) {
  return <div className={`card error-state fx-reveal ${className}`}>
    <span className="error-state-icon"><Icon name="alert" size={22} /></span>
    <div className="error-state-body">
      <strong>{title}</strong>
      <p className="error-message" role="alert">{message}</p>
      {(onRetry || children) && <div className="error-state-actions">
        {onRetry && <ReloadButton tone="primary" label={retryLabel} loadingLabel="Retrying…" loading={retrying} onClick={onRetry} />}
        {children}
      </div>}
    </div>
  </div>
}
