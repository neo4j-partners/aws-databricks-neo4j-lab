#!/usr/bin/env node

/**
 * Convert Excalidraw JSON files to SVG format using puppeteer.
 * Loads the official Excalidraw library in a headless browser to render SVGs.
 *
 * Usage: cd docs && node scripts/convert-excalidraw.js
 */

const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const IMAGES_DIR = path.join(__dirname, '..', 'images');

const HTML_TEMPLATE = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://unpkg.com/react@18.2.0/umd/react.production.min.js"></script>
  <script src="https://unpkg.com/react-dom@18.2.0/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@excalidraw/excalidraw@0.17.6/dist/excalidraw.production.min.js"></script>
</head>
<body>
  <div id="app"></div>
  <script>
    window.convertToSVG = async function(excalidrawData) {
      try {
        const { exportToSvg } = window.ExcalidrawLib;
        const { elements, appState, files } = excalidrawData;

        const svg = await exportToSvg({
          elements: elements || [],
          appState: {
            ...appState,
            exportWithDarkMode: false,
            exportBackground: true,
          },
          files: files || null,
        });

        return svg.outerHTML;
      } catch (error) {
        console.error('Error in convertToSVG:', error);
        throw error;
      }
    };

    window.conversionReady = true;
  </script>
</body>
</html>
`;

async function convertExcalidrawToSVG(page, inputFile, outputFile) {
  try {
    console.log(`Converting ${path.basename(inputFile)}...`);

    const excalidrawData = JSON.parse(fs.readFileSync(inputFile, 'utf8'));

    const svgString = await page.evaluate((data) => {
      return window.convertToSVG(data);
    }, excalidrawData);

    fs.writeFileSync(outputFile, svgString);
    console.log(`  ✓ Created ${path.basename(outputFile)}`);

    return true;
  } catch (error) {
    console.error(`  ✗ Error converting ${path.basename(inputFile)}:`);
    console.error(`    ${error.message}`);
    return false;
  }
}

async function convertAll() {
  console.log('Converting Excalidraw diagrams to SVG...\n');

  const files = fs.readdirSync(IMAGES_DIR)
    .filter(file => file.endsWith('.excalidraw'))
    .sort();

  if (files.length === 0) {
    console.log('No .excalidraw files found in docs/images/.');
    return;
  }

  console.log(`Found ${files.length} diagram(s) to convert.\n`);

  console.log('Launching headless browser...');
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setContent(HTML_TEMPLATE);
  await page.waitForFunction(() => window.conversionReady === true, { timeout: 30000 });
  console.log('Excalidraw library loaded.\n');

  let successCount = 0;

  for (const file of files) {
    const inputPath = path.join(IMAGES_DIR, file);
    const outputPath = path.join(IMAGES_DIR, file.replace('.excalidraw', '.svg'));

    const success = await convertExcalidrawToSVG(page, inputPath, outputPath);
    if (success) successCount++;
  }

  await browser.close();

  console.log(`\nConversion complete: ${successCount}/${files.length} files converted successfully.`);
  console.log(`Output directory: ${IMAGES_DIR}\n`);

  if (successCount < files.length) {
    process.exit(1);
  }
}

convertAll().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
