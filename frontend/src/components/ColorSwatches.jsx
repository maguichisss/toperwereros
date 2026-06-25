function contrastColor(hex) {
  const h = hex.replace('#', '')
  const r = parseInt(h.substring(0, 2), 16)
  const g = parseInt(h.substring(2, 4), 16)
  const b = parseInt(h.substring(4, 6), 16)
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.5 ? '#111' : '#fff'
}

export default function ColorSwatches({ colors, selectedIds, onChange }) {
  return (
    <div className="color-swatches">
      {colors.map((c) => {
        const isSelected = selectedIds.includes(c.id)
        return (
          <div
            key={c.id}
            className={`swatch ${isSelected ? 'selected' : ''}`}
            style={{ backgroundColor: c.hex, color: contrastColor(c.hex) }}
            title={c.name}
            data-name={c.name}
            onClick={() =>
              onChange(
                isSelected ? selectedIds.filter((id) => id !== c.id) : [...selectedIds, c.id]
              )
            }
          />
        )
      })}
    </div>
  )
}
