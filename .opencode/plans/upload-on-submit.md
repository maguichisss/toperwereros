# Upload image only on form submit instead of immediately on capture

## CameraCapture.jsx

1. Remove `import { uploadApi } from '../api/client.js';`
2. Remove `uploading` state (lines 9, 47, 51-65)
3. `capture()` function (lines 37-64):
   - Remove upload logic, keep blob → File creation
   - `setCaptured(file)` and `onCapture(file)` instead of `url`
4. `handleFileSelect()` (lines 52-65):
   - Remove upload logic, just `setCaptured(file)` and `onCapture(file)`
5. Preview: change `captured` from URL to File object
   - Preview needs `URL.createObjectURL(file)` instead of direct URL
   - Add cleanup of object URL on unmount/retake
6. Remove the `uploading` UI text, change preview to use local object URL

## ProductForm.jsx

1. Add `const [imageFile, setImageFile] = useState(null);`
2. Change `handleCameraCapture(url)` → `handleCameraCapture(file)`:
   - `setImageFile(file)`
   - `setImageUrl('')` (clear old URL)
3. Preview logic:
   - If `imageFile` exists: show `<img src={URL.createObjectURL(imageFile)} />`
   - Else if `imageUrl` exists: show `<img src={imageUrl} />` (existing product)
4. In `handleSubmit`, before creating/updating:
   - If `imageFile` is set: `const result = await uploadApi.upload(imageFile); url = result.image_url;`
   - Then use `url` in product data
5. Add cleanup: revoke `URL.createObjectURL(imageFile)` when component unmounts or `imageFile` changes
6. Keep `uploading` state for showing spinner during file upload
