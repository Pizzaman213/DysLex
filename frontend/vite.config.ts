import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import { readFileSync, existsSync, createReadStream, statSync } from 'fs';
import { viteStaticCopy } from 'vite-plugin-static-copy';

/** Serve ML model files from ml/models/ during dev (viteStaticCopy only runs at build time). */
function serveMLModels(): Plugin {
  return {
    name: 'serve-ml-models',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url?.startsWith('/models/')) {
          const clean = req.url.split('?')[0];
          const filePath = resolve(__dirname, '../ml', clean.slice(1));
          if (existsSync(filePath)) {
            const stat = statSync(filePath);
            res.writeHead(200, {
              'Content-Length': stat.size,
              'Content-Type': 'application/octet-stream',
              'Cache-Control': 'public, max-age=86400',
            });
            createReadStream(filePath).pipe(res);
            return;
          }
        }
        next();
      });
    },
  };
}

const enableHttps = process.env.VITE_ENABLE_HTTPS === 'true';
const certPath = resolve(__dirname, '../certs/dev/localhost+2.pem');
const keyPath = resolve(__dirname, '../certs/dev/localhost+2-key.pem');

const httpsConfig =
  enableHttps && existsSync(certPath) && existsSync(keyPath)
    ? { cert: readFileSync(certPath), key: readFileSync(keyPath) }
    : undefined;

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
  },
  plugins: [
    react(),
    serveMLModels(),
    viteStaticCopy({
      targets: [
        // Seq2seq T5 model files (primary model)
        {
          src: '../ml/models/quick_correction_seq2seq_v1/encoder_model*.onnx',
          dest: 'models/quick_correction_seq2seq_v1',
        },
        {
          src: '../ml/models/quick_correction_seq2seq_v1/decoder_model*.onnx',
          dest: 'models/quick_correction_seq2seq_v1',
        },
        {
          src: '../ml/models/quick_correction_seq2seq_v1/config.json',
          dest: 'models/quick_correction_seq2seq_v1',
        },
        {
          src: '../ml/models/quick_correction_seq2seq_v1/generation_config.json',
          dest: 'models/quick_correction_seq2seq_v1',
        },
        {
          src: '../ml/models/quick_correction_seq2seq_v1/tokenizer*',
          dest: 'models/quick_correction_seq2seq_v1',
        },
        {
          src: '../ml/models/quick_correction_seq2seq_v1/spiece.model',
          dest: 'models/quick_correction_seq2seq_v1',
        },
        {
          src: '../ml/models/quick_correction_seq2seq_v1/special_tokens_map.json',
          dest: 'models/quick_correction_seq2seq_v1',
        },
        // Base model dictionary + frequency files (still used for fallback)
        {
          src: '../ml/models/quick_correction_base_v1/correction_dict.json',
          dest: 'models/quick_correction_base_v1',
        },
        {
          src: '../ml/models/quick_correction_base_v1/frequency_dictionary_en_82_765.txt',
          dest: 'models/quick_correction_base_v1',
        },
        {
          src: '../ml/models/quick_correction_base_v1/frequency_dictionary_en_full.txt',
          dest: 'models/quick_correction_base_v1',
        },
        // ONNX Runtime WASM files
        {
          src: 'node_modules/onnxruntime-web/dist/ort-wasm-simd.wasm',
          dest: 'onnx',
        },
        {
          src: 'node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.wasm',
          dest: 'onnx',
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
    https: httpsConfig,
    proxy: {
      '/api': {
        target: enableHttps ? 'https://localhost:8000' : 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  optimizeDeps: {
    exclude: ['onnxruntime-web', 'onnxruntime-web/wasm', '@xenova/transformers'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          tiptap: ['@tiptap/core', '@tiptap/react', '@tiptap/starter-kit'],
          onnx: ['@xenova/transformers'],
          reactflow: ['@xyflow/react'],
        },
      },
    },
  },
});
