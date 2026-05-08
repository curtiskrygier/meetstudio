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
    },
    define: {
      'process.env.CLIENT_ID': JSON.stringify(env.CLIENT_ID || process.env.CLIENT_ID || ''),
      'process.env.CLOUD_PROJECT_NUMBER': JSON.stringify(env.CLOUD_PROJECT_NUMBER || process.env.CLOUD_PROJECT_NUMBER || ''),
    },
    resolve: {
      alias: { '@': path.resolve(__dirname, '.') },
    },
  };
});
