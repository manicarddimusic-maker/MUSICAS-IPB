/** Modo "artefato": página publicada dentro da Claude (sem service worker, rotas por #hash, download pela Claude). */
export const ARTEFATO = import.meta.env.MODE === 'artefato';

const BASE = import.meta.env.BASE_URL; // './' no artefato, '/' no site comum

/** Converte '/midias/x.jpg' em um caminho que funciona nos dois modos. */
export function caminho(p: string): string {
  return /^(https?:|data:|blob:)/.test(p) ? p : BASE + p.replace(/^\/+/, '');
}
