import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { ARTEFATO } from './ambiente';
import SincronizaHash, { caminhoInicial } from './SincronizaHash';
import App from './App';
import './styles.css';

/** Se o app quebrar por arquivo antigo em cache, recarrega uma vez sozinho. */
function recarregarUmaVez(motivo: string) {
  try {
    if (sessionStorage.getItem('recarregou') === '1') return false;
    sessionStorage.setItem('recarregou', '1');
  } catch {
    return false;
  }
  console.warn('Recarregando o app:', motivo);
  location.reload();
  return true;
}

window.addEventListener('error', (e) => {
  const msg = String((e as ErrorEvent).message ?? '');
  if (/dynamically imported module|Loading chunk|Importing a module script failed/i.test(msg)) {
    recarregarUmaVez(msg);
  }
});
window.addEventListener('unhandledrejection', (e) => {
  const msg = String((e.reason && (e.reason.message ?? e.reason)) ?? '');
  if (/dynamically imported module|Loading chunk|Importing a module script failed/i.test(msg)) {
    recarregarUmaVez(msg);
  }
});

class Protecao extends React.Component<{ children: React.ReactNode }, { erro: string | null }> {
  state = { erro: null as string | null };

  static getDerivedStateFromError(e: Error) {
    return { erro: e?.message ?? 'erro' };
  }

  componentDidCatch(e: Error) {
    if (/dynamically imported module|Loading chunk/i.test(e?.message ?? '')) recarregarUmaVez(e.message);
  }

  render() {
    if (this.state.erro) {
      return (
        <div className="aviso">
          <h1>Algo deu errado ao abrir esta página</h1>
          <p>Toque para tentar de novo.</p>
          <button onClick={() => location.reload()}>Recarregar</button>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Protecao>
      {ARTEFATO ? (
        <MemoryRouter initialEntries={[caminhoInicial()]}>
          <SincronizaHash />
          <App />
        </MemoryRouter>
      ) : (
        <BrowserRouter>
          <App />
        </BrowserRouter>
      )}
    </Protecao>
  </React.StrictMode>,
);

if (!ARTEFATO && 'serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .then((reg) => {
        reg.update().catch(() => {});
      })
      .catch(() => {});
  });
}
