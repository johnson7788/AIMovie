import path from 'path'
import { ConfigEnv, defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import Icons from 'unplugin-icons/vite'
import IconsResolver from 'unplugin-icons/resolver'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import compression from 'vite-plugin-compression';
import Inspect from 'vite-plugin-inspect'

const pathSrc = path.resolve(__dirname, './src')
export default defineConfig((ConfigEnv: ConfigEnv) => {
  const env = loadEnv(ConfigEnv.mode, process.cwd())
  return {
    base: '/aimovie/',
    resolve: {
      alias: {
        '@': pathSrc,
      },
    },
    build: {
      assetsDir: 'assets',
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules')) {
              return 'vendor';
            }
          }
        }
      },
    },
    plugins: [
      // bundleAnalyzer({ port: 8888, }),
      compression({
        // 指定要压缩的文件类型，默认为 .js 和 .css
        // ext: '.js',
        // 开启Gzip压缩
        algorithm: 'gzip',
        // 超过(n)k才打包
        threshold: 50 * 1024,
        // 是否删除原始文件，默认为 false
        deleteOriginFile: false
      }),
      vue(),
      AutoImport({
        imports: ['vue'],
        resolvers: [
          ElementPlusResolver(),
          IconsResolver({
            prefix: 'Icon',
          }),
        ],
        dts: path.resolve(__dirname, 'auto-imports.d.ts'),
        eslintrc: {
          enabled: true
        },
      }),
      Components({
        extensions: ['vue', 'md'],
        include: [/\.vue$/, /\.vue\?vue/, /\.md$/],
        resolvers: [
          IconsResolver({
            enabledCollections: ['ep'],
          }),
          ElementPlusResolver(),
        ],
        dts: path.resolve(__dirname, 'components.d.ts'),
      }),
      Icons({
        autoInstall: true,
      }),
      Inspect()
    ],
    server: {
      open: true,
      port: 36310,
      allowedHosts: true,
      // 接口代理（解决跨域）
      proxy: {
        "/local": {
          target: env.VITE_REQUEST_BASE_URL,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/local/, ""),
        }
      },
    },
  }
})
