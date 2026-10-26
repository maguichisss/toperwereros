# Add rotate button to camera capture

## CameraCapture.jsx

### New function `rotateImage()`
- Only runs if `captured` (File) exists
- Loads the File into an `Image` element
- Draws to a canvas with 90° rotation (swap width/height)
- Exports back to JPEG File
- Revokes old object URLs
- Updates `captured`, `previewUrl`, calls `onCapture(file)`

### UI change
Replace the Retake button section:
```
Before: <button className="btn btn-secondary" onClick={retake}>Repetir</button>
After:  <button className="btn btn-secondary" onClick={rotateImage}>Rotar</button>
        <button className="btn btn-secondary" onClick={retake}>Repetir</button>
```
