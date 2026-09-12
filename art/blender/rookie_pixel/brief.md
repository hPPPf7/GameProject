# Rookie pixel character — first Blender prototype

Reference: `7644fb54-0e4e-4a39-87a9-3b7ef5587027.png` supplied by the user.

- Three views of the same chibi explorer: broad gray/brown hair, a small cowlick,
  peach face, two dark vertical eyes, navy scarf, ochre coat, brown trousers,
  boots and a brown backpack with straps and a square clasp. Empty hands.
- Preserve the oversized head and short limbs. Head/hair occupies roughly
  40–45% of the full silhouette; no realistic facial anatomy or fine wrinkles.
- Coordinate system: Z up, -Y forward. Orthographic front, right-facing side,
  rear, and three-quarter cameras. Ground at Z=0.
- Palette: hair #8B847B, hair shadow #514B4A, skin #F4CA96, coat #B38647,
  scarf #304963, trousers #4B3B34, leather #765033, boots #67432B.
- Build simple bevelled forms and larger sculpted hair clumps. Use a small
  nearest-filtered atlas and discrete face shades, without glossy gradients.
- Intended output: editable .blend, a basic in-place walking rig, a pixel
  turnaround, animated previews and a standalone sheet for the existing inspector.
- The first prototype is not a final face rig or a seamless production skin.
  Deliberately separate rigid clothing/accessory pieces keep the style crisp.
- Preserve the initial Blender scene. Work in `Rookie_Pixel_Prototype`.

Workflow references reviewed: arjun988/blender-skills `blender-director`,
`character-artist`, `chibi-style`, `lowpoly-style`, `rigging`, `animation`,
and `references/reference-image-match.md`. Pixel-art-style could not be fetched;
pixel sampling and palette requirements are specified explicitly above.

Validation: compare the rendered silhouette and reference, inspect the gait in
side and three-quarter views, check weights, ground clearance and loop closure,
then verify the exported sheet with the project's SpriteSheet loader.
