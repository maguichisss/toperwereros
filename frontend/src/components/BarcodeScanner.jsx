import { useState, useEffect, useRef } from 'react';
import { Html5Qrcode, Html5QrcodeSupportedFormats } from 'html5-qrcode';

export default function BarcodeScanner({ onDetected, onCancel }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const scannerRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [cameraReady, setCameraReady] = useState(false);
  const [borderColor, setBorderColor] = useState('');

  useEffect(() => {
    let stopped = false;

    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment' }
        });
        if (stopped) return;
        streamRef.current = stream;
        const video = videoRef.current;
        if (!video) return;
        video.srcObject = stream;
        await video.play();
        if (stopped) return;

        const el = document.getElementById('_html5qr_temp') || document.createElement('div');
        el.id = '_html5qr_temp';
        el.style.display = 'none';
        if (!el.parentNode) document.body.appendChild(el);
        const scanner = new Html5Qrcode('_html5qr_temp', {
          formatsToSupport: Object.values(Html5QrcodeSupportedFormats).filter(v => typeof v === 'number')
        });
        scannerRef.current = scanner;

        if (!stopped) setCameraReady(true);
      } catch {
        onCancel();
      }
    }

    start();

    return () => {
      stopped = true;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
      }
    };
  }, []);

  async function handleCapture() {
    if (loading || !cameraReady) return;
    setLoading(true);
    setError('');
    setBorderColor('');

    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video || !video.videoWidth) {
      setLoading(false);
      setError('Error al capturar la imagen');
      return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    try {
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
      const file = new File([blob], 'barcode.png', { type: 'image/png' });
      const decoded = await scannerRef.current.scanFile(file, false);
      if (decoded) {
        setBorderColor('green');
        setTimeout(() => {
          if (streamRef.current) {
            streamRef.current.getTracks().forEach(t => t.stop());
          }
          onDetected(decoded);
        }, 400);
        return;
      }
      setBorderColor('red');
      setError('No se encontró código de barras');
      setTimeout(() => setBorderColor(''), 1500);
    } catch {
      setBorderColor('red');
      setError('No se encontró código de barras');
      setTimeout(() => setBorderColor(''), 1500);
    }
    setLoading(false);
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal barcode-modal" onClick={(e) => e.stopPropagation()}>
        <h2>Escanear código de barras</h2>
        <div
          className="scanner-viewfinder"
          style={{
            border: borderColor ? `3px solid ${borderColor}` : 'none',
            transition: 'border-color 0.2s'
          }}
        >
          {!cameraReady && !error && (
            <div className="scanner-loading">Iniciando cámara...</div>
          )}
          <video ref={videoRef} playsInline muted style={!cameraReady ? { display: 'none' } : {}} />
          <canvas ref={canvasRef} style={{ display: 'none' }} />
        </div>
        {loading && (
          <p style={{ textAlign: 'center', color: '#555', marginTop: '0.5rem' }}>
            Leyendo código de barras...
          </p>
        )}
        {error && (
          <p className="error-text" style={{ textAlign: 'center', marginTop: '0.5rem' }}>
            {error}
          </p>
        )}
        <div className="camera-controls" style={{ marginTop: '0.5rem' }}>
          <button
            type="button"
            className="shutter-btn"
            disabled={loading || !cameraReady}
            onClick={handleCapture}
          />
        </div>
        <div className="form-actions" style={{ marginTop: '0.5rem' }}>
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}
