# Front-End Changes

## Light Theme Variant (`frontend/style.css`)

Added a full light theme that can be activated by adding the `light-theme` class to `<body>`.

### New CSS variables (`body.light-theme`)

| Variable | Dark value | Light value | Notes |
|---|---|---|---|
| `--primary-color` | `#2563eb` | `#1d4ed8` | Slightly darker for WCAG AA contrast on white |
| `--primary-hover` | `#1d4ed8` | `#1e40af` | Deeper hover state |
| `--background` | `#0f172a` | `#f8fafc` | Near-white page background |
| `--surface` | `#1e293b` | `#ffffff` | White card/sidebar surface |
| `--surface-hover` | `#334155` | `#f1f5f9` | Subtle hover tint |
| `--text-primary` | `#f1f5f9` | `#0f172a` | Dark slate for body text (~17:1 contrast on white) |
| `--text-secondary` | `#94a3b8` | `#475569` | Slate-600 meets WCAG AA on white (4.7:1) |
| `--border-color` | `#334155` | `#e2e8f0` | Light separator lines |
| `--user-message` | `#2563eb` | `#1d4ed8` | User bubble background |
| `--assistant-message` | `#374151` | `#f1f5f9` | Assistant bubble background |
| `--shadow` | `rgba(0,0,0,0.3)` | `rgba(0,0,0,0.1)` | Lighter shadow |
| `--focus-ring` | `rgba(37,99,235,0.2)` | `rgba(29,78,216,0.25)` | Visible focus ring |
| `--welcome-bg` | `#1e3a5f` | `#eff6ff` | Welcome card tint (blue-50) |
| `--welcome-border` | `#2563eb` | `#bfdbfe` | Welcome card border (blue-200) |
| `--code-bg` | `rgba(0,0,0,0.25)` | `rgba(0,0,0,0.06)` | Inline/block code background |

### Smooth transitions

Added `transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease` to all major UI elements so switching themes animates smoothly instead of snapping.

Elements covered: `body`, `.sidebar`, `.chat-main`, `.chat-container`, `.chat-messages`, `.chat-input-container`, `.message-content`, `.stat-item`, `.suggested-item`, `#chatInput`, `#sendButton`, `.source-pill`, `.new-chat-btn`, `.stats-header`, `.suggested-header`, `.message-content code`, `.message-content pre`.

### Source pill overrides

The source pills used hardcoded `rgba(59,130,246,...)` / `#93c5fd` colours that only work on dark backgrounds. Added `body.light-theme .source-pill` overrides using navy-blue tones that maintain readability on white.

### How to activate

```js
document.body.classList.add('light-theme');    // enable light mode
document.body.classList.remove('light-theme'); // restore dark mode
```

Pair with `localStorage` to persist the user's preference across page loads.
