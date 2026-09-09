import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

export default function Toast({ message, type = 'error', duration = 4000, onClose }) {
  const [top, setTop] = useState(() => (window.visualViewport?.offsetTop || 0) + 16);

  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(onClose, duration);
    return () => clearTimeout(timer);
  }, [message, duration, onClose]);

  useEffect(() => {
    const vv = window.visualViewport;
    const update = () => setTop((vv?.offsetTop || 0) + 16);
    update();
    vv?.addEventListener('resize', update);
    vv?.addEventListener('scroll', update);
    return () => {
      vv?.removeEventListener('resize', update);
      vv?.removeEventListener('scroll', update);
    };
  }, [message]);

  if (!message) return null;

  return createPortal(
    <div className={`toast toast-${type}`} role="alert" style={{ top }} onClick={onClose}>
      <span>{message}</span>
      <span className="toast-close">&times;</span>
    </div>,
    document.body
  );
}