import { useEffect, useRef } from 'react'

export default function ConfirmDialog({ title, message, onConfirm, onCancel }) {
  const confirmRef = useRef(null)

  useEffect(() => {
    const previouslyFocused = document.activeElement;
    confirmRef.current?.focus()
    function handleKeyDown(e) {
      if (e.key === 'Escape') onCancel()
      if (e.key === 'Enter') onConfirm()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      if (previouslyFocused && typeof previouslyFocused.focus === 'function') previouslyFocused.focus()
    }
  }, [onConfirm, onCancel])

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div
        className="modal modal--narrow"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        onClick={e => e.stopPropagation()}
      >
        <h2 id="confirm-dialog-title">{title}</h2>
        <p className="confirm-dialog__message">{message}</p>
        <div className="form-actions">
          <button type="button" className="btn btn--secondary" onClick={onCancel}>Cancelar</button>
          <button type="button" className="btn btn--danger" ref={confirmRef} onClick={onConfirm}>Confirmar</button>
        </div>
      </div>
    </div>
  )
}