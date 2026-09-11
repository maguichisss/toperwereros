import { useEffect } from 'react'

export default function Lightbox({ imageUrl, name, onClose }) {
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label={name || 'Imagen'}>
      <button
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