// Metro selects .native.ts or .web.ts. This fallback also gives TypeScript a
// platform-independent module to resolve during static checks.
export { tokenStore } from './token.native';
