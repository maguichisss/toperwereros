import { useEffect } from 'react';

export default function Toast({ message, type = 'error', duration = 4000, onClose }) {
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(onClose, duration);
    return () => clearTimeout(timer);
  }, [message, duration, onClose]);

  if (!message) return null;

  return (
    <div className={`toast toast-${type}`} onClick={onClose}>
      <span>{message}</span>
      <span className="toast-close">&times;</span>
    </div>
  );
}
