# Mobile hamburger menu for navigation tabs

## App.jsx
- Add `menuOpen` state
- Add hamburger button between `<h1>` and `<nav>`
- `<nav>` gets `className={menuOpen ? 'nav-open' : ''}`
- Tab clicks close menu: `() => { setTab(t.key); setMenuOpen(false); }`

## index.css
- Add `.hamburger` styles (hidden on desktop, animated X)
- Add `position: relative` to `header`
- Media query ≤640px: show hamburger, hide nav by default, show when `.nav-open`
- Mobile nav: absolute dropdown full-width below header, stacked buttons
