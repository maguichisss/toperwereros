export default function Lightbox({ imageUrl, name, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div style={{ maxWidth: '90vw', maxHeight: '90vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={e => e.stopPropagation()}>
        <img src={imageUrl} alt={name} style={{ maxWidth: '100%', maxHeight: '90vh', objectFit: 'contain', borderRadius: 4 }} />
      </div>
    </div>
  )
}
