# README diagram and demo sources

## Product diagram

`which-product-light.svg` and `which-product-dark.svg` are editable SVGs.
They are adapted from [the SDK product diagram](https://github.com/browser-use/sdk/blob/bfc0140801caf6a4c518c811f03674135efbd4aa/docs/cloud/images/which-product-light.svg),
introduced in [SDK PR #241](https://github.com/browser-use/sdk/pull/241).

The README version shows three paths:

- Fully hosted cloud: OpenCode → Browser Use CLI → cloud browser.
- CLI: your existing agent → Browser Use CLI → local or cloud browser.
- Python library: your code → Browser Use agent → local or cloud browser.

Keep the light and dark SVGs structurally identical when changing the diagram.
The SDK source remains the reference for the hosted stack; this README adds the
Python-library path and omits the Playwright branch.

## Driving-test demo

The inline GIF is converted from [Johannes Dittrich's public driving-test video](https://x.com/mathisdittrich/status/2078619618265141560).
It preserves the full 20.4-second recording at 960×540, 10 frames per second,
with an infinite loop. The source recording already obscures the contact fields.
No demo footage was generated.

The GIF is hosted as a [GitHub attachment](https://github.com/user-attachments/assets/135885e8-1141-4e10-b719-bf690ae7d260)
so cloning the repository does not download the animation.
