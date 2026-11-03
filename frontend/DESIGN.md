# CRM Sofia Design System

## 0. Research Log

- Embedded refs: shortlisted operational minimalist and brutalist directions; picked a hybrid because Sofia is a dense internal CRM that needs clarity with a distinctive Scandinavian edge.
- Lazyweb: skipped because this is an existing product shell and the brief supplies a clear visual direction.
- Imagen drafts: skipped because the requested surface is an app shell, not a marketing hero.

## 1. Atmosphere & Identity

Sofia is a quiet operations room: white space, hard alignment, and visible structure. The signature is a narrow blue-grey rail with orange action marks, using borders and tonal shifts instead of soft SaaS cards.

## 2. Color

| Role | Token | Light | Dark | Usage |
|---|---|---|---|---|
| Surface primary | `--surface-primary` | `#FFFFFF` | `#101820` | App canvas |
| Surface secondary | `--surface-secondary` | `#F4F7F8` | `#16232D` | Rail, muted panels |
| Surface elevated | `--surface-elevated` | `#FFFFFF` | `#1C2C37` | Menus, dialogs |
| Text primary | `--text-primary` | `#17232C` | `#F4F7F8` | Headings and body |
| Text secondary | `--text-secondary` | `#526572` | `#B6C5CE` | Supporting copy |
| Text tertiary | `--text-tertiary` | `#8496A1` | `#7C909C` | Metadata |
| Border default | `--border-default` | `#C9D4DA` | `#344752` | Structure |
| Border subtle | `--border-subtle` | `#E6ECEF` | `#253640` | Quiet separators |
| Accent primary | `--accent-primary` | `#E56A2E` | `#F28B52` | Actions, active state |
| Accent hover | `--accent-hover` | `#BD4F1D` | `#FFAA78` | Hover |
| Status success | `--status-success` | `#2E7D68` | `#63B59E` | Positive state |
| Status warning | `--status-warning` | `#B56A22` | `#E5A65F` | Warning |
| Status error | `--status-error` | `#B84242` | `#EC7777` | Error |

Rules: orange is reserved for action and attention. Blue-grey carries structure. No gradients. No decorative color noise.

## 3. Typography

- Primary: system sans stack, using `Arial` first for a compact Scandinavian grotesk feel.
- Mono: `ui-monospace` for IDs, metrics, and technical metadata.

| Level | Size | Weight | Usage |
|---|---:|---:|---|
| Display | 40px | 700 | Key page title |
| H1 | 28px | 700 | Page title |
| H2 | 20px | 700 | Section title |
| H3 | 16px | 700 | Card title |
| Body | 15px | 400 | Main content |
| Body small | 13px | 400 | Supporting text |
| Caption | 11px | 700 | Labels and metadata |

## 4. Spacing & Layout

Base unit: 4px. App shell uses a fixed rail, a 56px topbar, and a scroll-owned main region. Content is capped at 1440px with 24px desktop gutters and 16px mobile gutters. Multi-column content collapses to one column below 768px.

## 5. Components

### Navigation rail
- Structure: brand block, grouped links, account actions.
- Variants: expanded 240px, collapsed 64px.
- States: default, hover, active, focus, disabled.
- Accessibility: semantic nav, `aria-current`, tooltip when collapsed.

### Data card
- Structure: bordered surface, header, content, optional footer.
- Variants: default and accent-marked.
- States: default, loading, empty, error.
- Depth: borders-only, no shadow.

### Action button
- Structure: native button with icon and label.
- States: default, hover, active, focus, disabled, loading.
- Accessibility: visible focus, one-line labels, semantic type.

### Field
- Labels sit above inputs. Errors sit below. Focus uses orange outline.

## 6. Motion & Interaction

Micro interactions use 120ms ease-out. Standard panel changes use 220ms ease-in-out. Only transform and opacity animate. Reduced motion disables non-essential animation.

## 7. Depth & Surface

Borders-only strategy. Use 1px blue-grey borders and subtle surface shifts. Do not add drop shadows to cards or navigation.

## 8. Accessibility Constraints & Accepted Debt

Target WCAG 2.2 AA. Body text must meet 4.5:1 contrast, focus states are visible, all navigation is keyboard reachable, and reduced motion is respected.

Accepted debt: visual QA across every protected route remains to be completed after the shell pass; no functionality or route contract is changed by this redesign.
