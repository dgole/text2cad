# Dust Port Adapter

## Description

Clip-on adapter for a circular saw dust exhaust port. Clips onto the rectangular
port rim, extends an arm to a screw hole for anchoring, and (eventually) turns
90° to connect to a dust collection hose.

## Reference

- `reference/saw_dust_port_exit.jpg` — photo of the dust port

## Build stages

| Stage | What it produces | What to check |
|-------|-----------------|---------------|
| `plate` | Flat frame matching port outline | Does the opening line up with the port? |
| `collar` | Frame + clip lip behind it | Does it snap onto the rim? |
| `mounting` | Collar + arm with screw hole | Does the screw hole align? |

## Parameters

| Name | Default | Description |
|------|---------|-------------|
| `PORT_WIDTH` | 42.0 mm | Width of port opening (PLACEHOLDER — measure!) |
| `PORT_HEIGHT` | 28.0 mm | Height of port opening (PLACEHOLDER — measure!) |
| `PORT_CORNER_RADIUS` | 3.0 mm | Corner fillet radius |
| `WALL` | 2.5 mm | Adapter wall thickness |
| `RIM_THICKNESS` | 2.0 mm | How far the port rim protrudes |
| `RIM_DEPTH` | 3.0 mm | Axial depth of the rim |
| `SCREW_HOLE_DIA` | 4.5 mm | Screw clearance hole diameter |
| `SCREW_OFFSET_Y` | 30.0 mm | Distance from port center to screw hole |
