# Product form: inline validation instead of Toast

## Goal
Replace Toast-based validation errors in ProductForm with native `required` attributes and inline error messages.

## Changes (ProductForm.jsx only)

### 1. Add `required` to name, code, price inputs
```jsx
<input ref={nameRef} required ... />
<input ref={codeRef} required ... />
<input ref={priceRef} required ... />
```

### 2. Remove manual validation for name/code/price
Delete these from `handleSubmit`:
```javascript
if (!name.trim()) { ... }
if (!code.trim()) { ... }
if (!price || isNaN(Number(price)) || Number(price) < 0) { ... }
```

### 3. Add state for category error
```javascript
const [categoryError, setCategoryError] = useState(false);
```

### 4. Replace Toast for missing category
In `handleSubmit`, change:
```javascript
if (!categoryId) { setError('Categoría requerida'); return; }
```
to:
```javascript
if (!categoryId) { setCategoryError(true); return; }
```

### 5. Clear error on chip click
In each chip `onClick`, add `setCategoryError(false)`:
```jsx
onClick={() => { setCategoryId(c.id); setCategoryError(false); }}
```

### 6. Show inline error below chips
```jsx
{categoryError && <p className="error-text">Selecciona una categoría</p>}
```

### 7. Keep Toast for server errors
The `<Toast>` at the bottom of the form is still used for backend errors (duplicate code, etc.) — no change.
