import { useRef, useState, useEffect, useCallback } from 'react';
import { uploadApi } from '../api/client.js';

export default function CameraCapture({ onCapture }) {
  const videoRef = useRef();
  const canvasRef = useRef();
  const [stream, setStream] = useState(null);
  const [captured, setCaptured] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [noCamera, setNoCamera] = useState(false);

  const startCamera = useCallback(async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 } },
      });
      setStream(s);
      if (videoRef.current) {
        videoRef.current.srcObject = s;
      }
    } catch {
      setNoCamera(true);
      setError('Acceso a cámara denegado o no disponible');
    }
  }, []);

  useEffect(() => {
    startCamera();
    return () => {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }
    };
  }, [startCamera]);

  function capture() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      const file = new File([blob], 'photo.jpg', { type: 'image/jpeg' });
      setUploading(true);
      try {
        const result = await uploadApi.upload(file);
        const url = result.image_url || result.url;
        setCaptured(url);
        onCapture(url);
      } catch (err) {
        setError(err.message);
      } finally {
        setUploading(false);
      }
    }, 'image/jpeg');
  }

  async function handleFileSelect(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const result = await uploadApi.upload(file);
      const url = result.image_url || result.url;
      setCaptured(url);
      onCapture(url);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  function retake() {
    setCaptured(null);
    setError('');
  }

  return (
    <div className="camera-container">
      {noCamera ? (
        <div style={{ padding: '0.5rem 0' }}>
          <p className="error-text">{error}</p>
          <p style={{ marginBottom: '0.5rem', color: '#555', fontSize: '0.9rem' }}>
            Selecciona una imagen desde tu dispositivo:
          </p>
          <input
            type="file"
            accept="image/*"
            onChange={handleFileSelect}
            disabled={uploading}
          />
        </div>
      ) : (
        <>
          {!captured && (
            <video ref={videoRef} autoPlay playsInline muted />
          )}
          {captured && (
            <img src={captured} alt="Captured" />
          )}
          <canvas ref={canvasRef} hidden />

          <div className="camera-controls">
            {!captured ? (
              <button
                type="button"
                className="shutter-btn"
                onClick={capture}
                disabled={uploading}
              />
            ) : (
              <button type="button" className="btn btn-secondary" onClick={retake}>
                Repetir
              </button>
            )}
          </div>
        </>
      )}

      {uploading && (
        <p style={{ fontSize: '0.8rem', color: '#555', marginTop: '0.25rem' }}>
          Subiendo imagen...
        </p>
      )}

      {captured && (
        <p style={{ fontSize: '0.8rem', color: '#4caf50', marginTop: '0.25rem' }}>
          Foto capturada
        </p>
      )}
    </div>
  );
}
