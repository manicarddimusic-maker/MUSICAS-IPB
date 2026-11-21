import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

/** Dentro da Claude só passa um "#nome" simples na barra: /hinos/hino-61  <->  #hinos-hino-61 */
const SECOES = ['hinos', 'canticos', 'salmos', 'palavra', 'lavras'];

export function hashParaCaminho(hash: string): string {
  const h = hash.replace(/^#/, '');
  for (const s of SECOES) {
    if (h === s) return `/${s}`;
    if (h.startsWith(s + '-') && h.length > s.length + 1) return `/${s}/${h.slice(s.length + 1)}`;
  }
  return '/';
}

export function caminhoParaHash(caminho: string): string {
  const partes = caminho.split('/').filter(Boolean);
  return partes.length ? '#' + partes.join('-') : '';
}

export function caminhoInicial(): string {
  try {
    return hashParaCaminho(window.location.hash);
  } catch {
    return '/';
  }
}

export default function SincronizaHash() {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    try {
      const alvo = caminhoParaHash(pathname);
      if (window.location.hash !== alvo) {
        history.replaceState(null, '', window.location.pathname + window.location.search + alvo);
      }
    } catch {
      /* a moldura pode não deixar mexer na barra: sem problema */
    }
  }, [pathname]);

  useEffect(() => {
    const aoMudar = () => navigate(hashParaCaminho(window.location.hash), { replace: true });
    window.addEventListener('hashchange', aoMudar);
    return () => window.removeEventListener('hashchange', aoMudar);
  }, [navigate]);

  return null;
}
