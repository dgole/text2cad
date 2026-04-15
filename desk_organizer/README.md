# Desk Organizer

## Description

A minimalist desktop / nightstand / side-table organizer. The overall form
is a solid rectangular prism with pockets cut into it:

- **2 TV remote slots** — rectangular pockets cut from the top, grouped on the left side
- **3 pen slots** — circular holes cut from the top, grouped on the right side
- **2 phone slots** — thin slots accessible from the front face at the bottom, open at the top so you can slide a phone in

```
Front view:                Top view:

┌─────────────────┐       ┌───────────────────────┐
│                 │       │ ┌─────┐ ┌─────┐  ○    │
│                 │       │ │     │ │     │  ○    │
│                 │       │ │ rm1 │ │ rm2 │  ○    │
│                 │       │ │     │ │     │ pens  │
│ ┌─────────────┐ │       │ └─────┘ └─────┘       │
│ │  phone 2    │ │       └───────────────────────┘
│ ┌─────────────┐ │
│ │  phone 1    │ │
└─┴─────────────┴─┘

Phone slots are horizontal mail-slot openings — the phone lays flat
and slides in from the front face. Slots are stacked at the bottom.
```

## Reference

Sketch provided by the human showing front, top, and side views.

## Build stages

| Stage     | What it produces                    | What to check                          |
|-----------|-------------------------------------|----------------------------------------|
| `block`   | Plain rectangular prism             | Overall size feels right on the desk   |
| `pockets` | Body + remote & pen pockets on top  | Pocket sizes fit remotes & pens        |
| `full`    | Complete part with phone slots      | Phone slides in/out of front slots     |

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

### Phone slots

| Key                        | Description                                         |
|----------------------------|-----------------------------------------------------|
| `phone_slots.count`        | Number of phone slots (stacked vertically)          |
| `phone_slots.width`        | Width of the slot opening on the front face (X)     |
| `phone_slots.gap`          | Height of the slot opening (Z) — phone thickness + clearance |
| `phone_slots.interior_depth` | How far back the phone slides in (Y)              |
| `phone_slots.spacing`      | Vertical gap (Z) between stacked phone slots        |
| `phone_slots.offset_x`    | X offset of the phone slot group from body center   |
| `phone_slots.offset_z`    | Z position of the bottom of the lowest slot         |

## Usage

```bash
cd desk_organizer

# Stage 1 — just the block
python part.py block

# Stage 2 — block + top pockets
python part.py pockets
python part.py pockets --remote-width 35 --pen-diameter 14

# Stage 3 — full part with phone slots
python part.py full
python part.py full --phone-width 85 --phone-gap 14
```
