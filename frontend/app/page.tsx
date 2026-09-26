import Link from "next/link";

export default function Home() {
  return (
    <main className="home-premium">
      <section className="home-premium-shell">
        <header className="home-premium-topbar">
          <div className="home-premium-brand" aria-label="BKO Services">
            <span className="home-premium-mark" aria-hidden="true">B</span>
            <span>
              <strong>BKO Services</strong>
              <small>Bamako</small>
            </span>
          </div>

          <div className="home-premium-nav">
            <Link className="home-premium-login" href="/connexion">
              Connexion client
            </Link>
            <Link className="home-premium-provider-login" href="/prestataire/connexion">
              Connexion prestataire
            </Link>
            <Link className="home-premium-become" href="/prestataire/devenir">
              Créer compte prestataire
            </Link>
          </div>
        </header>

        <div className="home-premium-grid">
          <div className="home-premium-copy">
            <span className="home-premium-badge">Services de proximité à Bamako</span>
            <h1>
              Trouvez le bon professionnel.
              <span> Rapidement.</span>
            </h1>
            <p>
              Décrivez votre besoin, recevez un prestataire vérifié et suivez
              chaque étape de l’intervention depuis votre téléphone.
            </p>

            <div className="home-premium-actions">
              <Link className="home-premium-primary" href="/connexion">
                Trouver un professionnel
              </Link>
              <Link className="home-premium-secondary" href="/connexion">
                Créer mon compte
              </Link>
            </div>

            <div className="home-premium-trust">
              <span><strong>✓</strong> Prestataires vérifiés</span>
              <span><strong>✓</strong> Suivi clair</span>
              <span><strong>✓</strong> Paiement et données sécurisés</span>
            </div>
          </div>

          <div className="home-premium-showcase" aria-hidden="true">
            <div className="home-phone-card">
              <div className="home-phone-head">
                <span className="home-phone-mini-mark">B</span>
                <div>
                  <strong>BKO Services</strong>
                  <small>Votre demande</small>
                </div>
                <span className="home-online-dot" />
              </div>

              <div className="home-phone-welcome">
                <small>Bonjour 👋</small>
                <strong>De quoi avez-vous besoin ?</strong>
              </div>

              <div className="home-service-grid">
                <div><span>⚡</span><strong>Électricité</strong></div>
                <div><span>🔧</span><strong>Plomberie</strong></div>
                <div><span>❄</span><strong>Climatisation</strong></div>
                <div><span>＋</span><strong>Voir plus</strong></div>
              </div>

              <div className="home-status-card">
                <div className="home-status-top">
                  <span>Intervention en cours</span>
                  <strong>En route</strong>
                </div>
                <div className="home-status-line"><span /></div>
                <div className="home-provider-mini">
                  <span>MK</span>
                  <div>
                    <strong>Moussa K.</strong>
                    <small>Prestataire vérifié</small>
                  </div>
                  <b>4.9 ★</b>
                </div>
              </div>
            </div>

            <div className="home-float-card home-float-verified">
              <span>✓</span>
              <div>
                <strong>Prestataire vérifié</strong>
                <small>Identité contrôlée</small>
              </div>
            </div>

            <div className="home-float-card home-float-fast">
              <span>↗</span>
              <div>
                <strong>Suivi simple</strong>
                <small>Chaque étape visible</small>
              </div>
            </div>
          </div>
        </div>

        <div className="home-premium-bottom">
          <article>
            <span>01</span>
            <div>
              <strong>Décrivez votre besoin</strong>
              <small>Quelques informations suffisent.</small>
            </div>
          </article>
          <article>
            <span>02</span>
            <div>
              <strong>Un professionnel est proposé</strong>
              <small>Selon son métier et sa zone.</small>
            </div>
          </article>
          <article>
            <span>03</span>
            <div>
              <strong>Suivez l’intervention</strong>
              <small>Jusqu’à votre confirmation finale.</small>
            </div>
          </article>
        </div>
      </section>
    </main>
  );
}
