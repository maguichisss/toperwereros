import { useState, useEffect, useRef, useCallback } from 'react';
import { productsApi } from '../api/client.js';
import { formatPrice } from '../utils.js';

export default function ProductSearchBox({ placeholder, onSelect, excludeIds = [] }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const timer = useRef(null);
  const boxRef = useRef(null);

  const search = useCallback(async (q) => {
    if (!q.trim()) { setResults([]); return; }
    try {
      const res = await productsApi.list({ q, perPage: 10 });
      setResults(res.products.filter(p => p.stock > 0 && !excludeIds.includes(p.id)));
      setShowResults(true);
    } catch {}
  }, [excludeIds]);

  function handleChange(value) {
    setQuery(value);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => search(value), 300);
  }

  useEffect(() => {
    function handleClick(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) {
        setShowResults(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  function select(product) {
    onSelect(product);
    setQuery('');
    setResults([]);
    setShowResults(false);
  }

  return (
    <div className="cart-search" ref={boxRef}>
      <input
        className="search-input"
        placeholder={placeholder}
        value={query}
        onChange={e => handleChange(e.target.value)}
        onFocus={() => results.length > 0 && setShowResults(true)}
        autoComplete="off"
        autoCorrect="off"
        spellCheck="false"
      />
      {showResults && results.length > 0 && (
        <div className="search-results">
          {results.map(p => (
            <div key={p.id} className="search-result-item" onClick={() => select(p)}>
              {p.image_url ? (
                <img className="result-thumb" src={p.image_url} alt="" />
              ) : (
                <div className="result-thumb result-thumb-empty" />
              )}
              <span className="result-name">{p.name}</span>
              <span className="result-code">{p.code}</span>
              {p.ubicacion && <span className="result-ubicacion">{p.ubicacion}</span>}
              <span className="result-price">${formatPrice(p.price)}</span>
              <span className="result-stock">Stock: {p.stock}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}