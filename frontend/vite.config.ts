import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';


function figmaAssetResolver() {
  return {
    name: 'figma-asset-resolver',
    resolveId(id) {
      if (id.startsWith('figma:asset/')) {
        const filename = id.replace('figma:asset/', '')
        return path.resolve(__dirname, 'src/assets', filename)
      }
    },
  }
}

function packageName(id: string): string | null {
  const normalized = id.replace(/\\/g, '/');
  const match = normalized.match(/node_modules\/(?:\.pnpm\/[^/]+\/node_modules\/)?(@?[^/]+)(?:\/([^/]+))?/);
  if (!match) return null;
  return match[1].startsWith('@') ? `${match[1]}/${match[2] ?? ''}` : match[1];
}

export default defineConfig({
  plugins: [
    figmaAssetResolver(),react(), tailwindcss()],
  build: {
    emptyOutDir: false,
    rollupOptions: {
      output: {
        manualChunks(id) {
          const pkg = packageName(id);
          if (!pkg) return undefined;
          if (['react', 'react-dom', 'react-router-dom'].includes(pkg)) return 'vendor-react';
          if (pkg.startsWith('@radix-ui/') || ['lucide-react', 'sonner', 'cmdk'].includes(pkg)) return 'vendor-ui';
          if (['recharts', 'reactflow'].includes(pkg)) return 'vendor-charts';
          if (['react-markdown', 'remark-gfm', 'react-syntax-highlighter'].includes(pkg)) return 'vendor-markdown';
          if (['markmap-lib', 'markmap-view', 'reveal.js', 'mermaid'].includes(pkg)) return 'vendor-resource';
          if (pkg.startsWith('@mui/') || pkg.startsWith('@emotion/')) return 'vendor-mui';
          return undefined;
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
