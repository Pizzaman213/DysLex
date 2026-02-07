import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import { viteStaticCopy } from 'vite-plugin-static-copy';

export default defineConfig({
  plugins: [
    react(),
    viteStaticCopy({
      targets: [
        {
          src: '../ml/models/quick_correction_base_v1/model.onnx',
          dest: 'models/quick_correction_base_v1',
        },
        {
          src: '../ml/models/quick_correction_base_v1/tokenizer*',
          dest: 'models/quick_correction_base_v1',
        },
        {
          src: '../ml/models/quick_correction_base_v1/config.json',
          dest: 'models/quick_correction_base_v1',
        },
        {
          src: '../ml/models/quick_correction_base_v1/vocab.txt',
          dest: 'models/quick_correction_base_v1',
        },
        {
          src: '../ml/models/quick_correction_base_v1/correction_dict.json',
          dest: 'models/quick_correction_base_v1',
        },
      ],
    }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  assetsInclude: ['**/*.md'],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    exclude: ['onnxruntime-web'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          tiptap: ['@tiptap/core', '@tiptap/react', '@tiptap/starter-kit'],
          onnx: ['onnxruntime-web'],
          reactflow: ['@xyflow/react'],
        },
      },
    },
  },
});
