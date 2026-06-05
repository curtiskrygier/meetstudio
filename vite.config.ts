import path from 'path';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  return {
    server: {
      port: 3000,
      host: '0.0.0.0',
      proxy: {
        '/ws': { target: 'ws://localhost:8080', ws: true },
      },
    },
    build: {
      outDir: 'dist',
      rollupOptions: {
        input: {
          index: path.resolve(__dirname, 'index.html'),
          main_stage: path.resolve(__dirname, 'main_stage.html'),
        },
      },
    },
    define: {
      'process.env.CLIENT_ID': JSON.stringify(process.env.CLIENT_ID || env.CLIENT_ID || ''),
      'process.env.CLOUD_PROJECT_NUMBER': JSON.stringify(process.env.CLOUD_PROJECT_NUMBER || env.CLOUD_PROJECT_NUMBER || ''),
      '__BUILD_TIME__': JSON.stringify(new Date().toISOString().slice(0, 16).replace('T', ' ')),
    },
    resolve: {
      alias: { '@': path.resolve(__dirname, '.') },
    },
  };
});
