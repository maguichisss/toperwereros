import { useEffect, useRef } from 'react'

export default function Lightbox({ imageUrl, name, onClose }) {
  const closeRef = useRef(null)

  useEffect(() => {
    const previouslyFocused = document.activeElement
    closeRef.current?.focus()
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      if (previouslyFocused && typeof previouslyFocused.focus === 'function') previouslyFocused.focus()
    }
  }, [onClose])

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label={name || 'Imagen'}>
      <button
        ref={closeRef}
        type="button"
        className="lightbox-close-btn"
        onClick={onClose}
        aria-label="Cerrar"
      >
        ✕
      </button>
      <div className="lightbox-stage" onClick={e => e.stopPropagation()}>
        <img src={imageUrl} alt={name} />
      </div>
    </div>
  )
}