# Notes For Upstream PR

## Context

These changes were validated against a real TiEclipse microscope configuration with:

- Hamamatsu camera
- Nikon TI autofocus / PFS devices (`TIPFSStatus`, `TIPFSOffset`)
- a broken `TIFilterBlock1` turret on the instrument side

The goal of these fixes was to make `mmgui` usable for live preview and basic runtime control on real hardware, not only on demo configurations.

## Branch

- local branch: `codex/live-buffer-runtime-controls`

## Fix 1. Live acquisition started too aggressively

### Symptom

- `Snap` worked
- `Live` could put the camera into an error state
- the issue was more likely at low exposure values

### Root cause

`pymmcore_gui.actions.core_actions.toggle_live` started live mode with:

- `startContinuousSequenceAcquisition(0)`

This requests the fastest possible acquisition loop, which was too aggressive on the tested hardware.

### Fix

Use the current exposure as the minimum live interval instead of `0 ms`.

### Validation

- live no longer immediately overloads the camera on the tested setup
- slower exposures produce correspondingly slower frame arrival as expected

## Fix 2. Preview consumed the wrong image API and did not drain the MMCore buffer

### Symptom

- the live preview window showed an `ndv.RingBuffer`
- the acquisition buffer counter kept climbing until saturation
- frames were being acquired but not effectively flushed from the MMCore circular buffer

### Root cause

The preview timer checked `getRemainingImageCount() > 0` but then read frames with:

- `getLastImage()`

instead of removing them from the circular buffer.

This meant preview updated visually from the last frame while the MMCore circular buffer itself could remain full.

### Fix

Drain the MMCore circular buffer with:

- `popNextImage()`

and display only the most recent drained frame.

This keeps the preview responsive while ensuring the acquisition buffer is actually consumed.

### Validation

- live preview remains responsive
- MMCore buffer no longer monotonically grows to saturation during normal preview

## Fix 3. Reduce preview-side memory usage

### Symptom

The preview widget used a local `ndv` ring buffer with capacity `100`, which is unnecessarily large for simple live preview and can consume a lot of RAM on large cameras.

### Root cause

The preview widget stored a local history although only the most recent frame was needed for the tested workflow.

### Fix

Reduce preview buffer capacity from `100` to `1`.

### Validation

- preview still works for live monitoring
- memory footprint is much lower

## Fix 4. Runtime toolbar for frequently used controls

### Motivation

On real hardware, operators needed faster access to:

- camera exposure
- autofocus / PFS live toggle
- autofocus full focus action

without going through the property browser every time.

### Fix

Add a dedicated runtime toolbar with:

- exposure control
- autofocus / PFS controls

The toolbar is placed on its own line to avoid colliding with the menu bar.

### UX refinement

Shutter controls were initially added there too, but removed again because they made the top toolbar visually confusing and could overlap the menu area on smaller windows.

## Hardware-specific notes

- `TIFilterBlock1` is broken on the tested microscope.
- Some observed timeouts during unrelated operations were therefore caused by broad system waits on a broken device, not by the stage move itself.
- That specific issue was addressed separately in `pymmcore-widgets`.

## Suggested PR framing

The upstream PR for `pymmcore-gui` can likely be presented as:

1. make live preview safer on real hardware by avoiding `0 ms` continuous acquisition startup
2. fix preview buffer consumption so the MMCore circular buffer is properly drained
3. reduce preview memory footprint for live-only use
4. expose a minimal runtime toolbar for common hardware controls

## Things To Mention Explicitly In PR

- fixes were validated on real microscope hardware, not only in simulation
- one device (`TIFilterBlock1`) was physically faulty during testing
- the preview buffer fix is independent from that hardware fault
- the toolbar changes are partly workflow-driven and may need maintainer feedback on preferred UX
