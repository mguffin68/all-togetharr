# Design System Specification

## 1. Overview & Creative North Star

**The Creative North Star: The Digital Curator**

This design system moves beyond the utility of a standard media server and enters the realm of a premium digital gallery. We are not building a "file manager"; we are building a curated experience that treats local data with the same reverence as a high-end editorial magazine. 

To break the "template" look, this system utilizes **intentional asymmetry** and **tonal depth**. By leveraging Inter's clean glyphs with generous tracking and high-contrast typographic scales, we create an interface that feels "airy" yet authoritative. The UI should feel like a series of physical layers—stacked sheets of fine paper and frosted glass—rather than a flat digital grid.

---

## 2. Colors & Surface Philosophy

### The Tonal Palette

Our palette is rooted in the interplay between warm whites and architectural greys, accented by a muted slate for functional focus.

*   **Background (Surface):** `#F9F9FB` – A cool, clean foundation.

*   **Primary (Action):** `#5F5E60` – Sophisticated charcoal for high-priority interactions.

*   **Accent/State:** Muted slate (derived from `primary_container`) for active indications.

### The "No-Line" Rule

**Explicit Instruction:** Designers are prohibited from using 1px solid borders to define sections. Layout boundaries must be established solely through background color shifts. For example, a `surface-container-low` section sitting on a `surface` background provides all the separation necessary.

### Surface Hierarchy & Nesting

Depth is achieved through the physical "stacking" of containers. 

1.  **Level 0 (Base):** `surface` (`#F9F9FB`)

2.  **Level 1 (Sub-sections):** `surface-container-low` (`#F2F4F6`)

3.  **Level 2 (Active Widgets):** `surface-container-lowest` (`#FFFFFF`)

### The "Glass & Gradient" Rule

To add "soul" to the dashboard, use **Glassmorphism** for floating overlays. Use `surface_container_lowest` at 80% opacity with a `20px` backdrop-blur. Main CTAs should utilize a subtle linear gradient from `primary` to `primary_dim` to avoid the "flat" look of utility software.

---

## 3. Typography

We use **Inter** exclusively. To achieve the editorial look, we utilize high tracking (letter-spacing) on headers and labels to create a sense of luxury and breathing room.

*   **Display (Display-LG/MD):** Used for server names or hero stats. *Tracking: -0.02em.*

*   **Headlines (Headline-SM):** Charcoal (`#1D1D1F`). Used for module titles. *Tracking: -0.01em.*

*   **Titles (Title-LG/MD):** Used for media titles. Bold, high-contrast.

*   **Body (Body-MD):** Medium Grey (`#6E6E73`). For metadata and descriptions. *Line-height: 1.6.*

*   **Labels (Label-SM):** All-caps, *Tracking: 0.1em*. Used for technical specs (e.g., "1080P", "TRANSCODING").

---

## 4. Elevation & Depth

### The Layering Principle

Do not use shadows to define every card. Instead, place a `surface-container-lowest` card on a `surface-container-low` background. The slight shift in hex value creates a "Soft Lift" that feels integrated into the OS.

### Ambient Shadows

When an element must float (e.g., a modal or a primary playback control), use **Ambient Shadows**:

*   **Blur:** 32px to 64px.

*   **Opacity:** 4% to 8%.

*   **Color:** Use a tinted version of `on_surface` (`#2D3338`) to mimic natural light.

### The "Ghost Border" Fallback

If accessibility requirements demand a border, use a **Ghost Border**: The `outline_variant` token at **15% opacity**. This provides a hint of structure without cluttering the visual field.

---

## 5. Components

### Modular Widgets (Cards)

*   **Structure:** No divider lines. Separate content using `16px` or `24px` vertical padding.

*   **Corner Radius:** `xl` (0.75rem) for main widgets; `md` (0.375rem) for nested elements.

*   **Background:** `surface_container_lowest`.

### Ghost Input Fields

*   **Visuals:** No background fill or heavy borders. Only a bottom stroke using `outline_variant` at 20% opacity. 

*   **States:** On focus, the stroke transitions to `primary` (`#5F5E60`) with a subtle `2px` thickness.

### Health Indicator Dots

*   **Online:** `primary_fixed` with a soft pulsing animation (0.4 opacity scale).

*   **Alert:** `error` (`#9F403D`).

*   **Styling:** 8px circles with a `4px` outer glow of the same color at 20% opacity.

### Buttons

*   **Primary:** Solid `primary` fill, `on_primary` text. No border.

*   **Secondary:** `surface_container_high` fill. 

*   **Tertiary/Ghost:** No fill. `primary` text. Use for low-emphasis actions like "Cancel" or "Edit."

### Media Lists

*   **Rule:** Forbid divider lines. Use `surface_container_low` as a hover state background to define rows. Use the Spacing Scale to create clear groupings.

---

## 6. Do's and Don'ts

### Do

*   **Do** use asymmetrical layouts (e.g., a wide 2/3 widget next to a narrow 1/3 health monitor).

*   **Do** embrace white space. If a layout feels "empty," increase the typography size rather than adding a border.

*   **Do** use `9999px` (full) rounding for status chips and tags to contrast with the `xl` card corners.

### Don't

*   **Don't** use pure black (`#000000`). Use `inverse_surface` (`#0C0E10`) for deep contrast.

*   **Don't** use standard "Drop Shadows." If you can't see the blur, it's too heavy.

*   **Don't** use icons without purpose. Every icon must be accompanied by text or have a universally understood function within the server context.

*   **Don't** use 100% opaque lines to separate content. Use tonal shifts.