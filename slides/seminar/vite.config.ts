import { defineConfig } from 'vite'

// Keep straight quotes and apostrophes exactly as typed in slides.md.
export default defineConfig({
  slidev: {
    markdown: {
      markdownSetup(md) {
        md.options.typographer = false
      },
    },
  },
})
