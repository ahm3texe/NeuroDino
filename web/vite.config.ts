import fs from 'node:fs';

import {defineConfig} from 'vite';

export default defineConfig({
  // Relative base so the build works on any static host or sub-path.
  base: './',
  plugins: [{
    name: 'publish-checkpoint',
    // The scheduled deploy downloads this to continue the same timeline.
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'checkpoint.json',
        source: fs.readFileSync('src/timeline/checkpoint.json', 'utf8'),
      });
    },
  }],
});
