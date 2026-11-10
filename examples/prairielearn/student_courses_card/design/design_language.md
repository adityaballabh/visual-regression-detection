# PrairieLearn UI design standards

This guide summarizes the design language and UI conventions visible in the PrairieLearn
repository. It is intended to help contributors make new UI feel consistent with the existing
product. It is a practical guide to current patterns, not a complete or formally maintained design
system; follow the nearby implementation when a page has a more specific established pattern.

## Design principles

- **Prefer familiar, consistent interactions.** Reuse established page layouts, shared components,
  and interaction patterns rather than creating a one-off control for a common task.
- **Keep interfaces clear and focused.** Use concise labels, make the primary action apparent, and
  present related information together.
- **Make accessibility part of the design.** Support keyboard use, visible focus, understandable
  labels, sufficient contrast, and responsive text and layouts.
- **Use color to reinforce meaning, not to carry it alone.** Pair visual status or category
  differences with text, icons, or another perceivable cue.

## Visual language

### Layout and components

- PrairieLearn's application UI is built primarily with Bootstrap and React. Use the existing
  Bootstrap layout and utility classes where they fit.
- Before building a reusable control, check `apps/prairielearn/src/components/` and
  `packages/ui/`. Prefer a shared component when an equivalent already exists; use
  `@prairielearn/ui` for components intended to be shared across applications.
- Use React Bootstrap for basic controls that have a dedicated Bootstrap component. For more
  complex interactive controls, follow the existing React Aria patterns in `packages/ui/`.
- Keep page-specific UI with its page, and keep visual overrides scoped to that feature rather than
  changing global styles for a local need.
- Design for the available space: pages may use narrow panes, scrolling regions, or smaller
  screens. Avoid fixed dimensions when they would cause content to clip or become unusable.

### Typography, labels, and icons

- Use sentence case for titles, buttons, and other UI labels (for example, “Save course”).
- Prefer concise, plain-language labels that describe the action or information.
- Use Bootstrap Icons for new icons. Icons that convey information or an action need an accessible
  name; decorative icons should be hidden from assistive technology.
- Don't use visual emphasis alone to communicate meaning. Keep labels and supporting text available
  when color or an icon also signals status.

### Color and status

- Prefer Bootstrap's semantic CSS variables, such as `--bs-body-color`, `--bs-body-bg`, and
  `--bs-primary`, over hard-coded colors. This helps UI follow application themes.
- Use the repository's `color-*` badge classes for the established colored badge treatment. The
  available palette and rendered examples are maintained in
  [`apps/prairielearn/public/stylesheets/colors.scss`]
  and [`docs/course/colors.html`](course/colors.html). If changing that palette, also update the
  corresponding Python color lookup as described in the stylesheet.
- Use contextual Bootstrap styles for common states such as success, warning, and danger. Make sure
  the state is also described in text or otherwise available without color perception.
- Check text and control contrast against their actual backgrounds, including in themed and
  interactive states.

## Interaction and accessibility

- All interactive controls should work with a keyboard and show a visible focus state. Preserve
  expected keyboard behavior when adding custom interactions.
- Use semantic HTML and the correct control for the task. Give inputs programmatic labels, and
  connect validation messages to their inputs; invalid fields should expose `aria-invalid` and
  reference the associated error with `aria-errormessage` where applicable.
- Give icon-only buttons an accessible name. Provide useful alternative text for meaningful images,
  and avoid redundant labels for decorative imagery.
- Ensure hover-only affordances are also available on keyboard focus. Do not make hover the only
  way to discover or use an action.
- Respect reduced-motion preferences when introducing nonessential animation.
- Test layouts with longer text and resized viewports; avoid truncating essential information
  without a way to inspect it.

For content-specific accessibility guidance, see
[`docs/question/accessibility.md`](question/accessibility.md).

## Choosing where to make a UI change

- For a page-specific visual change, edit the page's React component or its feature stylesheet.
- For a repeated control or pattern, first look for an existing shared component; if the pattern is
  genuinely reusable, consider adding it to `packages/ui/`.
- For a global visual change, verify that it is meant to affect all relevant pages before changing
  shared or global styles.
- For hydrated React pages, the server page often supplies data and mounts the editor or component;
  the rendered interface itself may live in a component under that page's `components/` directory.

## Notes on scope

The repository contains established implementation conventions and shared visual primitives, but
this guide does not prescribe a complete brand identity, font scale, spacing scale, or exhaustive
component specification. Where this guide describes a convention inferred from existing code, use
the closest maintained component or local pattern as the source of truth.
