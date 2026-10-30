import fs from 'node:fs';

import {defineConfig} from 'vite';

export default defineConfig({
  // Relative base so the build works on any static host or sub-path.
  base: './',
  plugins: [{
    name: 'publish-checkpoint-and-paper',
    // The scheduled deploy downloads this to continue the same timeline.
    generateBundle() {
      this.emitFile({
        type: 'asset',
        fileName: 'checkpoint.json',
        source: fs.readFileSync('src/timeline/checkpoint.json', 'utf8'),
      });
      // The paper, served with the page: links to github.com cannot open
      // inside the Hugging Face Space's frame.
      for (const name of ['neurodino-en.pdf', 'neurodino.pdf']) {
        this.emitFile({type: 'asset', fileName: `paper/${name}`, source: fs.readFileSync(`../paper/${name}`)});
      }
    },
  }],
});
