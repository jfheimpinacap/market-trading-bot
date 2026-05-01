export function Topbar() {
  return (
    <header className="public-topbar" role="banner">
      <div className="public-topbar__row public-topbar__row--primary">
        <div className="topbar__brand">Web Ventas Genérica</div>
        <a className="topbar__action topbar__action--whatsapp" href="https://wa.me/0000000000" aria-label="WhatsApp">
          WhatsApp
        </a>
        <a className="topbar__action topbar__action--login" href="/">
          Panel
        </a>
      </div>

      <div className="public-topbar__row public-topbar__row--secondary">
        <button className="topbar__categories" type="button" aria-label="Abrir categorías">
          <span aria-hidden="true">☰</span>
          <span>Categorías</span>
        </button>

        <div className="topbar__search" role="search">
          <input type="search" placeholder="Buscar productos" aria-label="Buscar productos" />
          <button type="button" aria-label="Buscar">🔍</button>
        </div>

        <nav className="topbar__actions" aria-label="Accesos rápidos">
          <a className="topbar__action" href="#contacto">Contacto</a>
          <a className="topbar__action" href="#cotizar">Cotizar</a>
        </nav>
      </div>
    </header>
  );
}
