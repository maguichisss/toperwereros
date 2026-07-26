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
        onClick={onClose}
        aria-label="Cerrar"
        style={{
          position: 'fixed', top: 16, right: 16,
          background: 'rgba(0,0,0,0.5)', border: 'none', color: '#fff',
          fontSize: '1.5rem', width: 40, height: 40, borderRadius: '50%',
          cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
          zIndex: 101
        }}
      >✕</button>
      <div style={{ maxWidth: '90vw', maxHeight: '90vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={e => e.stopPropagation()}>
        <img src={imageUrl} alt={name} style={{ maxWidth: '100%', maxHeight: '90vh', objectFit: 'contain', borderRadius: 4 }} />
      </div>
    </div>
  )
}
