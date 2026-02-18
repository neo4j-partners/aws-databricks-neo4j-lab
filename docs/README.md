# Documentation

This directory contains documentation and architecture diagrams for the workshop.

## Structure

```
docs/
├── images/              # Architecture diagrams (.excalidraw source + generated .svg/.png)
├── scripts/             # Documentation tooling
│   └── convert-excalidraw.js   # Converts .excalidraw files to SVG
├── DATA_ARCHITECTURE.md # Full data schema and model documentation
├── package.json         # Node.js dependencies for doc tooling
└── README.md            # This file
```

## Generating Diagram Images

Architecture diagrams are authored as [Excalidraw](https://excalidraw.com/) files in `images/`. To generate SVG versions from the `.excalidraw` source files:

### Prerequisites

- Node.js 18+
- npm

### Install Dependencies

```bash
cd docs
npm install
```

This installs [Puppeteer](https://pptr.dev/) (headless Chromium), which is used to load the Excalidraw library and render SVGs.

### Convert Diagrams

```bash
npm run convert-diagrams
```

This finds all `.excalidraw` files in `images/`, converts each to `.svg`, and writes the output alongside the source files in `images/`.

### Editing Diagrams

To edit a diagram, open the `.excalidraw` file at [excalidraw.com](https://excalidraw.com/) (drag and drop or use Open), make changes, and save the file back. Then re-run `npm run convert-diagrams` to regenerate the SVG.
