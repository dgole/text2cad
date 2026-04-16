# Desk Organizer

## Description

A minimalist desktop / nightstand / side-table organizer. The overall form
is a solid rectangular prism with pockets cut into it:

- **4 TV remote slots** — rectangular pockets cut from the top, grouped on the left side
- **4 pen slots** — circular holes cut from the top, grouped on the right side
- **2 phone slots** — thin slots accessible from the front face (+X side) at the bottom
  (bottom slot is taller than the top slot)

For printability the body is **split horizontally** into two halves joined by
alignment pins (dowel joint):

- **Bottom half** — contains phone slots + pin holes on the split face.
  Rotated so phone openings face up. No overhangs.
- **Top half** — contains remote & pen pockets + pin holes on the split face.
  Flipped so pocket openings face up. No overhangs.
- **Pegs** — simple cylinders printed separately (×4), pressed into the
  holes on both halves during assembly.

```
Front view (+Y face):      Top view:                              Side view (+X face):

┌─────────────────┐       ┌─────────────────────────────────┐   ┌──────────┐
│                 │       │ ┌────┐┌────┐┌────┐┌────┐  ○    │   │          │
│                 │       │ │    ││    ││    ││    │  ○    │   │          │
│                 │       │ │rm1 ││rm2 ││rm3 ││rm4 │  ○    │   │          │
│   TOP HALF      │       │ │    ││    ││    ││    │  ○    │   │ TOP HALF │
│                 │       │ └────┘└────┘└────┘└────┘ pens  │   │          │
│- - - - - - - - -│ split │- - - - - - - - - - - - - - - - │   │- -pins- -│ split
│   BOTTOM HALF   │       │  ●                          ●  │   │          │
│                 │       │                                │   │──────────│ ← phone 2
│                 │       │  ●                          ●  │   │══════════│ ← phone 1
└─────────────────┘       └─────────────────────────────────┘   └──────────┘

Phone slots open on the SIDE face (+X). Phones slide in long-wise.
● = alignment pin positions (near corners)
```

## Reference

Sketch provided by the human showing front, top, and side views.

## Build stages

| Stage     | What it produces                         | What to check                          |
|-----------|------------------------------------------|----------------------------------------|
| `block`   | Plain rectangular prism                  | Overall size feels right on the desk   |
| `pockets` | Body + remote & pen pockets on top       | Pocket sizes fit remotes & pens        |
| `full`    | Complete part with phone slots           | Phone slides in/out of side slots      |
| `bottom`  | **Printable** bottom half (rotated)       | Phone slots open upward, pin holes visible |
| `top`     | **Printable** top half (flipped)          | Pockets open upward, pin holes visible |
| `peg`     | **Printable** single alignment peg        | Print 4 of these                       |

## Parameters

All parameters live in [`config.json`](config.json) — the single source of truth.
CLI flags override config values for one-off tweaks.

### Body

| Key              | Description                          |
|------------------|--------------------------------------|
| `body.width`     | Overall width (X dimension)          |
| `body.depth`     | Overall depth (Y dimension)          |
| `body.height`    | Overall height (Z dimension)         |
| `body.wall`      | Minimum wall thickness               |
| `body.fillet`    | Fillet radius on vertical edges      |

### Remote slots

| Key                         | Description                                      |
|-----------------------------|--------------------------------------------------|
| `remote_slots.count`        | Number of remote slots                           |
| `remote_slots.width`        | Width of each slot (X)                           |
| `remote_slots.depth`        | Depth of each slot (Y)                           |
| `remote_slots.pocket_depth` | How deep the pocket is cut from the top (Z)      |
| `remote_slots.spacing`      | Gap between adjacent remote slots                |
| `remote_slots.fillet`       | Corner fillet radius inside each pocket          |
| `remote_slots.offset_x`    | X offset of the slot group center from body center |

### Pen slots

| Key                       | Description                                        |
|---------------------------|----------------------------------------------------|
| `pen_slots.count`         | Number of pen holes                                |
| `pen_slots.diameter`      | Diameter of each pen hole                          |
| `pen_slots.pocket_depth`  | How deep the hole is cut from the top (Z)          |
| `pen_slots.spacing`       | Center-to-center spacing between pen holes (along Y) |
| `pen_slots.offset_x`     | X offset of the pen group center from body center  |

### Split / alignment pins

| Key                    | Description                                          |
|------------------------|------------------------------------------------------|
| `split.z`              | Z height where body splits into two halves           |
| `split.pin_diameter`   | Diameter of alignment pins                           |
| `split.pin_height`     | Total pin height (half in each piece)                |
| `split.pin_clearance`  | Extra diameter added to holes for friction fit       |
| `split.pin_inset_x`   | How far pins are inset from X edges                  |
| `split.pin_inset_y`   | How far pins are inset from Y edges                  |

### Phone slots

| Key                           | Description                                       |
|-------------------------------|---------------------------------------------------|
| `phone_slots.count`           | Number of phone slots (stacked vertically)        |
| `phone_slots.width`           | Width of slot opening on the side face (Y span)   |
| `phone_slots.gap_bottom`      | Height of bottom slot (Z)                         |
| `phone_slots.gap_top`         | Height of top slot (Z)                            |
| `phone_slots.interior_length` | How far the phone extends into the body (X)       |
| `phone_slots.spacing`         | Vertical gap (Z) between stacked phone slots      |
| `phone_slots.offset_y`       | Y offset of slot opening center on the side face  |
| `phone_slots.offset_z`       | Z position of the bottom of the lowest slot       |

## Usage

```bash
cd projects/desk_organizer

# Reference stages
python part.py block
python part.py pockets
python part.py full

# Printable halves
python part.py bottom
python part.py top

# Alignment pegs (print 4)
python part.py peg

# Override example
python part.py top --split-z 50 --pen-diameter 14
```
