import { useState, useEffect, useRef } from 'react';
import { productsApi, uploadApi, colorsApi } from '../api/client.js';
import ColorSwatches from './ColorSwatches.jsx';
import CameraCapture from './CameraCapture.jsx';
import BarcodeScanner from './BarcodeScanner.jsx';
import Toast from './Toast.jsx';

export default function ProductForm({ product, categories, onSave, onCancel }) {
  const [name, setName] = useState(product?.name ?? '');
  const [code, setCode] = useState(product?.code ?? '');
  const [stock, setStock] = useState(product?.stock ?? 1);
  const [description, setDescription] = useState(product?.description ?? '');
  const [ubicacion, setUbicacion] = useState(product?.ubicacion ?? '');
  const [price, setPrice] = useState(product?.price ?? '');
  const [categoryId, setCategoryId] = useState(product?.category_id ?? '');
  const [imageUrl, setImageUrl] = useState(product?.image_url ?? '');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [categoryError, setCategoryError] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [showScanner, setShowScanner] = useState(false);
  const [colors, setColors] = useState([]);
  const [selectedColorIds, setSelectedColorIds] = useState(
    product?.colors?.map((c) => c.id) ?? []
  );
  const codeRef = useRef(null);
  const nameRef = useRef(null);
  const priceRef = useRef(null);
  useEffect(() => {
    colorsApi.list().then(setColors).catch(() => {});
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (!categoryId) { setCategoryError(true); return; }

    try {
      const data = {
        name: name.trim(),
        code: code.trim(),
        stock: Number(stock),
        description: description.trim() || null,
        ubicacion: ubicacion.trim() || null,
        price: Number(price),
        categoryId: Number(categoryId),
        imageUrl: imageUrl || null,
        colorIds: selectedColorIds,
      };
      if (product) {
        await productsApi.update(product.id, data);
      } else {
        await productsApi.create(data);
      }
      onSave();
    } catch (err) {
      setError(err.message);
      if (err.message.toLowerCase().includes('código') || err.message.toLowerCase().includes('codigo')) {
        codeRef.current?.focus();
      }
    }
  }

  function handleCameraCapture(url) {
    setImageUrl(url);
    setShowCamera(false);
  }

  function handleBarcode(code) {
    setCode(code.replace(/[^A-Za-z0-9-]/g, ''));
    setShowScanner(false);
  }

  return (
    <>
      <div className="modal-overlay" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{product ? 'Editar Producto' : 'Añadir Producto'}</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Código</label>
            <div className="code-input-wrap">
              <input
                ref={codeRef}
                type="text"
                required
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/[^A-Za-z0-9-]/g, ''))}
              />
              <button type="button" className="btn-scan" onClick={() => setShowScanner(true)} title="Escanear código de barras">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
                  <circle cx="12" cy="13" r="4"/>
                </svg>
              </button>
            </div>
          </div>
          <div className="form-group">
            <label>Nombre</label>
              <input
                ref={nameRef}
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
          </div>
          <div className="form-row">
            <div className="form-group">
              <label>Precio ($)</label>
              <input
                ref={priceRef}
                type="number"
                step="0.01"
                min="0"
                required
                value={price}
                onChange={(e) => setPrice(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Cantidad</label>
              <input
                type="number"
                min="0"
                value={stock}
                onChange={(e) => setStock(e.target.value)}
              />
            </div>
          </div>
          <div className="form-group">
            <label>Categoría</label>
            <div className="category-chips">
              {categories.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className={`chip ${Number(categoryId) === c.id ? 'chip-active' : ''}`}
                  onClick={() => { setCategoryId(c.id); setCategoryError(false); }}
                >
                  {c.name}
                </button>
              ))}
            </div>
            {categoryError && <p className="error-text">Selecciona una categoría</p>}
          </div>
          <div className="form-group">
            <label>Imagen</label>
            {imageUrl && (
              <div className="image-preview" style={{ marginBottom: '0.5rem' }}>
                <img src={imageUrl} alt="Preview" />
                <button
                  type="button"
                  className="btn btn-danger"
                  style={{ marginTop: '0.25rem' }}
                  onClick={() => setImageUrl('')}
                >
                  Eliminar
                </button>
              </div>
            )}
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setShowCamera(!showCamera)}
              >
                {showCamera ? 'Cancelar cámara' : 'Tomar foto'}
              </button>
            </div>
            {showCamera && (
              <CameraCapture onCapture={handleCameraCapture} />
            )}
          </div>
          <div className="form-group">
            <label>Colores</label>
            <ColorSwatches
              colors={colors}
              selectedIds={selectedColorIds}
              onChange={setSelectedColorIds}
            />
          </div>
          <div className="form-group">
            <label>Descripción</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Ubicación</label>
            <input
              value={ubicacion}
              onChange={(e) => setUbicacion(e.target.value)}
              placeholder="Ej: Bodega A, estante 3"
            />
          </div>
          <Toast message={error} type="error" onClose={() => setError('')} />
          <div className="form-actions">
            <button type="button" className="btn btn-secondary" onClick={onCancel}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary">
              {product ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </form>
      </div>
    </div>
    {showScanner && (
      <BarcodeScanner
        onDetected={handleBarcode}
        onCancel={() => setShowScanner(false)}
      />
    )}
    </>
  );
}
